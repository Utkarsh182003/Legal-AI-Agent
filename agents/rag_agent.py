from pydantic_ai import Agent
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any, Optional
import json
import logging

from models.document_models import DocumentAnalysisResult, RAGResponse, KnowledgeGraph, Node, Edge, Paragraph
from utils.redis_cache import RedisCache

logger = logging.getLogger(__name__)

class RAGAgent(Agent[RAGResponse]):
    """
    Agent responsible for handling Retrieval Augmented Generation (RAG) queries.
    It leverages the extracted structured data (including the Knowledge Graph)
    and the full document text to provide concise and accurate answers.
    """
    def __init__(self, model: Any, cache: Optional[RedisCache] = None):
        super().__init__(model=model, output_type=RAGResponse)
        self.cache = cache
        self.document_analysis_result: Optional[DocumentAnalysisResult] = None # Store the analyzed document

    def load_document_context(self, analysis_result: DocumentAnalysisResult):
        """Loads the analyzed document into the agent for querying."""
        self.document_analysis_result = analysis_result
        logger.info(f"RAGAgent loaded context for document: {analysis_result.file_name}")

    async def _retrieve_context(self, query: str) -> Dict[str, Any]:
        """
        Retrieves relevant context based on the query.
        This version provides comprehensive structured data to the LLM.
        """
        if not self.document_analysis_result:
            logger.warning("No document context loaded for RAG agent.")
            return {"context_text": "", "relevant_snippets": [], "source_nodes": []}

        # Context components for the LLM
        context_parts = []
        relevant_snippets_for_response = [] # Snippets directly pulled
        source_node_ids_for_response = [] # Node IDs pulled

        # 1. Provide the full DocumentAnalysisResult as JSON
        full_analysis_json = self.document_analysis_result.model_dump_json(indent=2)
        context_parts.append(f"--- Full Document Analysis Result (JSON) ---\n{full_analysis_json}")

        # 2. Add relevant text snippets based on keyword matching (for additional detail)
        query_lower = query.lower()
        max_snippet_chars = 500 # Limit snippet length
        
        # Search relevant paragraphs for keyword
        for paragraph in self.document_analysis_result.paragraphs:
            if query_lower in paragraph.text.lower():
                start_index = max(0, paragraph.text.lower().find(query_lower) - 50)
                end_index = min(len(paragraph.text), start_index + max_snippet_chars)
                snippet = paragraph.text[start_index:end_index]
                if len(paragraph.text) > max_snippet_chars: # Add ellipsis if truncated
                    snippet = snippet.strip() + "..." if end_index < len(paragraph.text) else snippet.strip()
                relevant_snippets_for_response.append(snippet)
                if len(relevant_snippets_for_response) >= 3: # Limit number of snippets
                    break
        
        if relevant_snippets_for_response:
            context_parts.append(f"--- Relevant Document Snippets ---\n" + "\n".join(relevant_snippets_for_response))

        # 3. Add Knowledge Graph (optional, depending on query type, but include for completeness)
        kg_summary_text = ""
        if self.document_analysis_result.knowledge_graph:
            kg_nodes_info = []
            kg_edges_info = []
            for node in self.document_analysis_result.knowledge_graph.nodes:
                if query_lower in node.name.lower() or any(query_lower in str(v).lower() for v in node.attributes.values()):
                    kg_nodes_info.append(node.model_dump_json(indent=2))
                    source_node_ids_for_response.append(node.id) # Captures node ID for response

            for edge in self.document_analysis_result.knowledge_graph.edges:
                if query_lower in edge.type.lower() or (edge.source_id in source_node_ids_for_response) or (edge.target_id in source_node_ids_for_response):
                    kg_edges_info.append(edge.model_dump_json(indent=2))
            
            if kg_nodes_info:
                kg_summary_text += "Knowledge Graph Nodes:\n" + "\n".join(kg_nodes_info) + "\n"
            if kg_edges_info:
                kg_summary_text += "Knowledge Graph Edges:\n" + "\n".join(kg_edges_info) + "\n"

        if kg_summary_text:
            context_parts.append(f"--- Knowledge Graph Data ---\n{kg_summary_text}")

        # Combine all context parts
        full_context_text = "\n\n".join(context_parts)
            
        return {
            "context_text": full_context_text,
            "relevant_snippets": relevant_snippets_for_response,
            "source_nodes": source_node_ids_for_response
        }


    async def run(self, query: str) -> RAGResponse:
        """
        Processes a user query using RAG.
        """
        if not self.document_analysis_result:
            return RAGResponse(answer="Please load a document first.", confidence="Low")

        print(f"\n--- Processing RAG query: '{query}' for document '{self.document_analysis_result.file_name}' ---")

        # Retrieve context
        retrieved_data = await self._retrieve_context(query)
        context_text = retrieved_data["context_text"]
        relevant_snippets = retrieved_data["relevant_snippets"]
        source_node_ids = retrieved_data["source_nodes"]

        if not context_text:
            return RAGResponse(answer="Could not find relevant context in the document.", confidence="Low")

        # Construct LLM prompt
        llm_prompt = (
            f"You are a helpful legal AI assistant. Your goal is to answer the user's question "
            f"concisely and accurately, strictly based on the provided 'Document Context'.\n"
            f"The 'Document Context' includes the full JSON representation of the document analysis, "
            f"relevant text snippets, and knowledge graph data. "
            f"Prioritize information from the structured JSON and knowledge graph as it is the most precise. "
            f"If the exact answer is not explicitly stated or directly derivable from the provided context, "
            f"respond with 'I don't have enough information in the provided context to answer that.' "
            f"Do not make up information.\n\n"
            f"--- Document Context ---\n{context_text}\n\n"
            f"--- User Question ---\n{query}\n\n"
            f"--- Instructions ---\n"
            f"1. Provide a concise answer to the question.\n"
            f"2. Indicate your confidence level (High, Medium, Low) in the answer based on the clarity and directness of the context.\n"
            f"3. List any specific text snippets or Knowledge Graph Node IDs from the provided context that directly support your answer.\n"
            f"4. Ensure your output strictly conforms to the Pydantic schema for RAGResponse."
        )

        try:
            rag_result = await super().run(llm_prompt)
            final_rag_response = rag_result.output
            final_rag_response.relevant_snippets = relevant_snippets
            final_rag_response.source_nodes = source_node_ids
            
            print(f"RAG Answer: {final_rag_response.answer}")
            return final_rag_response

        except ValidationError as e:
            logger.error(f"LLM output validation error for RAG query: {e.errors()}")
            return RAGResponse(answer=f"Failed to generate valid RAG response due to schema mismatch. Details: {e.errors()}", confidence="Low")
        except Exception as e:
            logger.error(f"Unexpected error during RAG query processing: {e}")
            return RAGResponse(answer=f"An error occurred during RAG processing: {e}", confidence="Low")

