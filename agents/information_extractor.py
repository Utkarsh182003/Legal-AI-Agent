from pydantic_ai import Agent
from pydantic import BaseModel, ValidationError
from typing import Type, List, Dict, Any, Optional
import json
import uuid
from datetime import date

from models.document_models import (
    DocumentContent, DocumentAnalysisResult, DocumentMetadata,
    Party, DateClause, MonetaryValue, DefinedTerm,
    Paragraph, Sentence,
    ExtractedEntities
)
from models.legal_clauses import (
    IndemnificationClause, ForceMajeureClause, GoverningLawClause,
    ConfidentialityClause, TerminationClause
)
from utils.redis_cache import RedisCache
from pydantic_ai.models.google import GoogleModel

class InformationExtractionAgent(Agent[ExtractedEntities]):
    """
    Agent responsible for orchestrating multi-stage information extraction
    from legal documents using different LLM models and specific Pydantic schemas,
    and then compiling the results into a comprehensive DocumentAnalysisResult.
    """
    def __init__(self, model: Any, cache: Optional[RedisCache] = None):
        super().__init__(model=model, output_type=ExtractedEntities)
        self.model = model
        self.cache = cache

    async def run(self, document_content: DocumentContent) -> DocumentAnalysisResult:
        """
        The main public method for this agent, orchestrating the document content
        to LLM structured extraction and then packaging it into a comprehensive DocumentAnalysisResult.
        """
        document_id = str(uuid.uuid4())
        cache_key = f"full_analysis_cache:{document_id}"

        if self.cache:
            cached_analysis_result_dict = self.cache.get(cache_key)
            if cached_analysis_result_dict:
                print(f"Retrieving full analysis for {document_content.file_name} from cache.")
                try:
                    return DocumentAnalysisResult.model_validate(cached_analysis_result_dict)
                except ValidationError as e:
                    print(f"Cached full analysis for {document_content.file_name} is invalid, re-running analysis: {e}")
                    self.cache.delete(cache_key)

        print(f"Starting LLM structured extraction for {document_content.file_name} using Gemini 1.5 Flash... (Attempting to extract monetary value reason)")

        text_for_llm = document_content.text_content
        CONTEXT_LIMIT_CHARS = 10000
        if len(text_for_llm) > CONTEXT_LIMIT_CHARS:
            print(f"Document longer than {CONTEXT_LIMIT_CHARS} chars, truncating for LLM context.")
            text_for_llm = text_for_llm[:CONTEXT_LIMIT_CHARS]

        prompt = (
            f"You are an expert legal document analyst. Your task is to accurately extract "
            f"all structured information from the following legal document snippet based on the "
            f"provided Pydantic schema for ExtractedEntities. "
            f"Pay close attention to names, roles, dates, monetary values (including the *specific reason* for the amount, such as 'rent', 'fine for breach of conduct', etc.), " 
            f"defined terms, and the specific details of clauses. "
            f"Also, provide a concise overall summary of the document in the 'analysis_summary' field. "
            f"Crucially, identify the single most important 'effective date' or 'document date' "
            f"and populate the 'document_effective_date' field in the schema. "
            f"Ensure all extracted data strictly conforms to the schema's types and descriptions. "
            f"If information for a field is not explicitly present, return an empty list for lists or None for optional fields.\n\n"
            f"--- Document Snippet ---\n{text_for_llm}\n\n"
            f"--- Instructions ---"
        )

        extracted_entities: Optional[ExtractedEntities] = None
        try:
            agent_run_result = await super().run(prompt)
            extracted_entities = agent_run_result.output
            print("Successfully extracted structured entities using LLM via Agent.run().output.")

        except ValidationError as e:
            print(f"Pydantic validation error for LLM output: {e.errors()}")
            print(f"Raw LLM Output was expected to be a dictionary matching ExtractedEntities, but validation failed.")
            extracted_entities = ExtractedEntities()
        except Exception as e:
            print(f"Unexpected error during LLM response generation by Agent.run(): {e}")
            if "context_length_exceeded" in str(e).lower():
                 print("Critical: Context length exceeded even with Gemini 1.5 Flash. This should not happen with the current setup. Review schema/text size.")
            extracted_entities = ExtractedEntities()


        if not extracted_entities:
            print("LLM extraction resulted in an empty or invalid ExtractedEntities object.")
            extracted_entities = ExtractedEntities()

        primary_effective_date = extracted_entities.document_effective_date
        if not primary_effective_date and extracted_entities.dates:
            effective_date_keywords = [
                "effective date", "policy date", "agreement date",
                "execution date", "document date", "date"
            ]
            
            for keyword in effective_date_keywords:
                for date_item in extracted_entities.dates:
                    if date_item.date_type and keyword in date_item.date_type.lower():
                        primary_effective_date = date_item.date_value
                        print(f"Using '{date_item.date_type}' from extracted_dates as primary effective date: {primary_effective_date}")
                        break
                if primary_effective_date:
                    break
            
            if not primary_effective_date and extracted_entities.dates:
                primary_effective_date = extracted_entities.dates[0].date_value
                print(f"No specific 'effective date' keyword found, using first extracted date: {primary_effective_date}")


        metadata = DocumentMetadata(
            document_type=extracted_entities.document_type or "Uncategorized",
            title=extracted_entities.document_title or document_content.file_name,
            effective_date=primary_effective_date,
            parties_summary=extracted_entities.parties,
            jurisdiction=extracted_entities.jurisdiction
        )

        extracted_clauses_dict: Dict[str, List[Dict]] = {
            "IndemnificationClause": extracted_entities.indemnification_clauses,
            "ForceMajeureClause": extracted_entities.force_majeure_clauses,
            "GoverningLawClause": extracted_entities.governing_law_clauses,
            "ConfidentialityClause": extracted_entities.confidentiality_clauses,
            "TerminationClause": extracted_entities.termination_clauses,
        }
        extracted_clauses_dict = {k: v for k, v in extracted_clauses_dict.items() if v}

        analysis_result = DocumentAnalysisResult(
            document_id=document_id,
            file_name=document_content.file_name,
            metadata=metadata,
            extracted_parties=extracted_entities.parties,
            extracted_dates=extracted_entities.dates,
            extracted_monetary_values=extracted_entities.monetary_values,
            extracted_defined_terms=extracted_entities.defined_terms,
            extracted_clauses_summary=extracted_clauses_dict,
            compliance_findings=[],
            analysis_summary=extracted_entities.analysis_summary or "No summary generated by LLM.",
            full_text_content=document_content.text_content,
            paragraphs=document_content.paragraphs
        )

        if self.cache:
            self.cache.set(cache_key, analysis_result.model_dump(), ex=3600)
            print(f"Full analysis for {document_content.file_name} cached.")

        return analysis_result

