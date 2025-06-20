# agents/compliance_analyzer.py (UPDATED - Fixed ExtractedEntities Import)

from pydantic_ai import Agent
from pydantic import BaseModel, ValidationError, Field
from typing import List, Dict, Any, Optional
import json

from models.document_models import (
    DocumentAnalysisResult, ComplianceRule, ComplianceFinding, DocumentContent,
    ExtractedEntities # FIXED: Import ExtractedEntities here
)
from utils.redis_cache import RedisCache

# This is the Pydantic model for the LLM's output when assessing a single rule.
class RuleAssessmentOutput(BaseModel):
    """
    Structured output for the LLM's assessment of a single compliance rule.
    """
    rule_id: str = Field(description="The ID of the rule being assessed.")
    is_compliant: bool = Field(description="True if the document is compliant with this rule, False otherwise.")
    finding_details: Optional[str] = Field(None, description="Detailed explanation of the compliance status or non-compliance reasons.")
    relevant_text_snippets: List[str] = Field(default_factory=list, description="List of exact text snippets from the document that are relevant to this finding.")
    recommendation: Optional[str] = Field(None, description="Specific recommendation to achieve compliance or mitigate risk for this rule.")


class ComplianceAnalyzerAgent(Agent[List[ComplianceFinding]]):
    """
    Agent responsible for analyzing extracted document information against
    a set of predefined compliance rules and identifying risks.
    It uses an LLM to perform nuanced assessments where direct rule matching isn't sufficient.
    """
    def __init__(self, model: Any, cache: Optional[RedisCache] = None):
        super().__init__(model=model)
        self.model = model # The LLM model (e.g., GoogleModel)
        self.cache = cache
        self.compliance_rules: List[ComplianceRule] = self._load_compliance_rules()

    def _load_compliance_rules(self) -> List[ComplianceRule]:
        """
        Loads predefined compliance rules. In a real application, these might come
        from a database, configuration file, or an admin UI.
        For now, they are hardcoded examples.
        """
        rules = [
            ComplianceRule(
                rule_id="NDA-001",
                name="Confidentiality Period Check (NDA)",
                description="Ensures that a Confidentiality Clause specifies a duration of at least 3 years for confidentiality obligations.",
                check_criteria="Look for a 'ConfidentialityClause' and verify if the 'duration_years' field is present and >= 3.",
                severity_level="High",
                recommendation_template="Ensure the Confidentiality Clause specifies a duration of at least 3 years to adequately protect sensitive information."
            ),
            ComplianceRule(
                rule_id="LEASE-001",
                name="Lease Agreement - Rent Amount Presence",
                description="Verifies that a rent amount is explicitly stated in a Lease Agreement.",
                check_criteria="Check if the 'monetary_values' list contains an item with 'reason' as 'Rent' and a valid 'amount'.",
                severity_level="Critical",
                recommendation_template="The Lease Agreement must explicitly state the rent amount to avoid financial disputes."
            ),
            ComplianceRule(
                rule_id="GDPR-001",
                name="GDPR Data Minimization Principle",
                description="Checks if the document mentions principles related to data minimization (e.g., collecting only necessary data).",
                check_criteria="Analyze the document summary and relevant sections for mentions of 'data minimization', 'collect only necessary data', or similar phrases.",
                severity_level="Medium",
                recommendation_template="Consider adding stronger language around data minimization principles to align more closely with GDPR requirements."
            ),
             ComplianceRule(
                rule_id="TERMINATION-001",
                name="Termination Notice Period Check",
                description="Ensures a termination clause exists and specifies a notice period.",
                check_criteria="Check if a 'TerminationClause' exists and if its 'notice_period_days' is specified.",
                severity_level="High",
                recommendation_template="A termination clause should clearly define the notice period (in days) required for contract termination to prevent ambiguity."
            )
        ]
        return [ComplianceRule.model_validate(rule.model_dump()) for rule in rules]

    async def _assess_rule_with_llm(self, rule: ComplianceRule, document_text: str, extracted_data: ExtractedEntities) -> RuleAssessmentOutput:
        """
        Uses the LLM to assess a single compliance rule against the document content and extracted data.
        """
        prompt = (
            f"You are a legal compliance expert. Your task is to assess the compliance of a document "
            f"against a specific rule. Provide a clear 'is_compliant' (True/False) status, "
            f"detailed 'finding_details', relevant 'relevant_text_snippets', and a 'recommendation'.\n\n"
            f"--- Compliance Rule ---\n"
            f"Rule ID: {rule.rule_id}\n"
            f"Rule Name: {rule.name}\n"
            f"Rule Description: {rule.description}\n"
            f"Check Criteria: {rule.check_criteria}\n\n"
            f"--- Document Snippet (Relevant Portion) ---\n"
            f"{document_text[:5000]}...\n\n"
            f"--- Extracted Structured Data (JSON) ---\n"
            f"{extracted_data.model_dump_json(indent=2)}\n\n"
            f"--- Instructions ---\n"
            f"Based on the Rule Criteria, the Document Snippet, and the Extracted Structured Data, "
            f"determine if the document is compliant with Rule '{rule.rule_id}'. "
            f"Provide your assessment in the following JSON format matching the Pydantic schema for RuleAssessmentOutput. "
            f"Be precise in 'finding_details' and include exact 'relevant_text_snippets' that support your finding. "
            f"If non-compliant, provide a 'recommendation' based on the rule's template or your expertise.\n"
        )
        
        try:
            assessment_agent = Agent(model=self.model, output_type=RuleAssessmentOutput)
            assessment_result = await assessment_agent.run(prompt)
            return assessment_result.output

        except ValidationError as e:
            print(f"LLM output validation error for rule {rule.rule_id}: {e.errors()}")
            return RuleAssessmentOutput(
                rule_id=rule.rule_id,
                is_compliant=False,
                finding_details=f"LLM failed to produce valid assessment output: {e.errors()}",
                relevant_text_snippets=[],
                recommendation=f"Internal system error during rule assessment. Check LLM output format."
            )
        except Exception as e:
            print(f"Error assessing rule {rule.rule_id} with LLM: {e}")
            return RuleAssessmentOutput(
                rule_id=rule.rule_id,
                is_compliant=False,
                finding_details=f"An unexpected error occurred during LLM rule assessment: {e}",
                relevant_text_snippets=[],
                recommendation=f"Internal system error during rule assessment."
            )


    async def run(self, analysis_result: DocumentAnalysisResult) -> DocumentAnalysisResult:
        """
        Performs compliance analysis on a DocumentAnalysisResult.
        Updates the analysis_result with compliance findings.
        """
        print(f"Starting compliance analysis for {analysis_result.file_name}...")
        findings: List[ComplianceFinding] = []

        document_full_text = analysis_result.full_text_content
        # Recreate ExtractedEntities to ensure proper type, especially for caching and passing to LLM
        # This re-instantiation helps ensure consistency, although Pydantic usually handles this.
        extracted_entities = ExtractedEntities(
            document_type=analysis_result.metadata.document_type,
            document_title=analysis_result.metadata.title,
            document_effective_date=analysis_result.metadata.effective_date,
            parties=analysis_result.extracted_parties,
            jurisdiction=analysis_result.metadata.jurisdiction,
            dates=analysis_result.extracted_dates,
            monetary_values=analysis_result.extracted_monetary_values,
            defined_terms=analysis_result.extracted_defined_terms,
            analysis_summary=analysis_result.analysis_summary,
            indemnification_clauses=analysis_result.extracted_clauses_summary.get("IndemnificationClause", []),
            force_majeure_clauses=analysis_result.extracted_clauses_summary.get("ForceMajeureClause", []),
            governing_law_clauses=analysis_result.extracted_clauses_summary.get("GoverningLawClause", []),
            confidentiality_clauses=analysis_result.extracted_clauses_summary.get("ConfidentialityClause", []),
            termination_clauses=analysis_result.extracted_clauses_summary.get("TerminationClause", []),
        )


        for rule in self.compliance_rules:
            print(f"  - Assessing rule: {rule.name} ({rule.rule_id})...")
            
            assessment_output = await self._assess_rule_with_llm(
                rule=rule,
                document_text=document_full_text,
                extracted_data=extracted_entities
            )

            # Create a ComplianceFinding from the LLM's assessment
            finding = ComplianceFinding(
                rule_id=rule.rule_id,
                rule_description=rule.description, # Use rule.description from the rule object
                is_compliant=assessment_output.is_compliant,
                finding_details=assessment_output.finding_details,
                relevant_text_snippets=assessment_output.relevant_text_snippets,
                recommendation=assessment_output.recommendation or rule.recommendation_template,
                severity=rule.severity_level
            )
            findings.append(finding)
            print(f"    Result: {'COMPLIANT' if finding.is_compliant else 'NON-COMPLIANT'} (Severity: {finding.severity})")

        analysis_result.compliance_findings = findings
        print(f"Compliance analysis for {analysis_result.file_name} complete.")
        return analysis_result
