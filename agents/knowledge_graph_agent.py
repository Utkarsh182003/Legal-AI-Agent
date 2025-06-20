# agents/knowledge_graph_agent.py (UPDATED - Fixed Document Node Attributes)

from pydantic_ai import Agent
from pydantic import ValidationError
from typing import List, Dict, Any, Optional
import uuid
import re # For sanitizing IDs

from models.document_models import (
    DocumentAnalysisResult, Node, Edge, KnowledgeGraph,
    Party, DateClause, MonetaryValue, DefinedTerm, ExtractedEntities # Added ExtractedEntities
)
from utils.redis_cache import RedisCache

class KnowledgeGraphAgent(Agent[KnowledgeGraph]):
    """
    Agent responsible for constructing a Knowledge Graph from the extracted
    structured information in a DocumentAnalysisResult.
    """
    def __init__(self, model: Any, cache: Optional[RedisCache] = None):
        super().__init__(model=model) # LLM might be used for complex relationship extraction later
        self.cache = cache
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []
        self.id_map: Dict[str, str] = {} # To map entity names/values to unique IDs

    def _sanitize_id(self, text: str) -> str:
        """Sanitizes text to create a valid ID."""
        text = text.strip().replace(" ", "_").replace(".", "").replace(",", "")
        return re.sub(r'[^\w-]', '', text)[:50] # Remove non-alphanumeric, limit length

    def _add_node(self, node_id: str, node_type: str, name: str, attributes: Dict[str, Any] = None) -> Node:
        """Adds a node if it doesn't already exist and returns it."""
        if node_id not in self.id_map:
            # Ensure attributes is a dictionary, even if None is passed
            final_attributes = attributes if attributes is not None else {}
            node = Node(id=node_id, type=node_type, name=name, attributes=final_attributes)
            self.nodes.append(node)
            self.id_map[node_id] = node_id # Mark as added
            return node
        else:
            # If node already exists, find and return it (simplified for demo)
            for existing_node in self.nodes:
                if existing_node.id == node_id:
                    return existing_node
            # This should ideally not happen if id_map is consistent
            raise ValueError(f"Node {node_id} found in id_map but not in nodes list.")


    def _add_edge(self, source_id: str, target_id: str, edge_type: str, attributes: Dict[str, Any] = None):
        """Adds an edge between two existing nodes."""
        if source_id not in self.id_map or target_id not in self.id_map:
            print(f"Warning: Cannot add edge {edge_type} from {source_id} to {target_id}. One or both nodes do not exist.")
            return

        final_attributes = attributes if attributes is not None else {}
        edge = Edge(source_id=source_id, target_id=target_id, type=edge_type, attributes=final_attributes)
        self.edges.append(edge)

    async def run(self, analysis_result: DocumentAnalysisResult) -> DocumentAnalysisResult:
        """
        Constructs a Knowledge Graph from the DocumentAnalysisResult.
        """
        print(f"Starting Knowledge Graph construction for {analysis_result.file_name}...")
        self.nodes = [] # Reset for each run
        self.edges = []
        self.id_map = {}

        doc_id = f"Document:{analysis_result.document_id}"
        doc_name = analysis_result.file_name
        doc_type = analysis_result.metadata.document_type
        doc_title = analysis_result.metadata.title or doc_name

        # Add the main document node
        self._add_node(doc_id, "Document", doc_title, {
            "file_name": doc_name,
            # Removed "file_type": analysis_result.metadata.file_type as it doesn't exist there
            "document_type": doc_type, # Add document_type as an attribute of the document node
            "analysis_summary": analysis_result.analysis_summary
        })

        # Add Document Metadata relationships
        if analysis_result.metadata.effective_date:
            date_id = f"Date:{analysis_result.metadata.effective_date.isoformat()}"
            self._add_node(date_id, "Date", analysis_result.metadata.effective_date.isoformat(), {"type": "Effective Date"})
            self._add_edge(doc_id, date_id, "HAS_EFFECTIVE_DATE")
        
        if analysis_result.metadata.jurisdiction:
            jurisdiction_id = f"Jurisdiction:{self._sanitize_id(analysis_result.metadata.jurisdiction)}"
            self._add_node(jurisdiction_id, "Jurisdiction", analysis_result.metadata.jurisdiction)
            self._add_edge(doc_id, jurisdiction_id, "GOVERNED_BY")

        # Process Parties
        for party in analysis_result.extracted_parties:
            party_id = f"Party:{self._sanitize_id(party.name)}"
            self._add_node(party_id, "Party", party.name, party.model_dump())
            self._add_edge(doc_id, party_id, "HAS_PARTY", {"role": party.role})

        # Process Dates
        for date_clause in analysis_result.extracted_dates:
            date_id = f"Date:{self._sanitize_id(str(date_clause.date_value))}-{self._sanitize_id(date_clause.date_type or '')}"
            self._add_node(date_id, "Date", str(date_clause.date_value), date_clause.model_dump())
            self._add_edge(doc_id, date_id, "REFERENCES_DATE", {"type": date_clause.date_type})

        # Process Monetary Values
        for mv in analysis_result.extracted_monetary_values:
            mv_id = f"MonetaryValue:{mv.amount}_{mv.currency}"
            self._add_node(mv_id, "MonetaryValue", f"{mv.amount} {mv.currency}", mv.model_dump())
            self._add_edge(doc_id, mv_id, "HAS_MONETARY_VALUE", {"reason": mv.reason})

        # Process Defined Terms
        for dt in analysis_result.extracted_defined_terms:
            term_id = f"DefinedTerm:{self._sanitize_id(dt.term)}"
            self._add_node(term_id, "DefinedTerm", dt.term, dt.model_dump())
            self._add_edge(doc_id, term_id, "DEFINES", {"definition": dt.definition})

        # Process Clauses
        for clause_type, clauses_list in analysis_result.extracted_clauses_summary.items():
            for clause_dict in clauses_list:
                clause_id = f"Clause:{clause_type}:{uuid.uuid4().hex[:8]}"
                self._add_node(clause_id, "Clause", clause_type.replace("Clause", ""), {"text_excerpt": clause_dict.get('clause_text', '')[:100], **clause_dict})
                self._add_edge(doc_id, clause_id, f"HAS_{clause_type.upper()}")

                if clause_type == "ConfidentialityClause" and clause_dict.get("duration_years"):
                    duration_id = f"Duration:{clause_dict['duration_years']}Years"
                    self._add_node(duration_id, "Duration", f"{clause_dict['duration_years']} Years")
                    self._add_edge(clause_id, duration_id, "HAS_DURATION")
                
        final_knowledge_graph = KnowledgeGraph(nodes=self.nodes, edges=self.edges)

        analysis_result.knowledge_graph = final_knowledge_graph

        if self.cache:
            # When caching DocumentAnalysisResult, it will internally use its model_dump()
            # which correctly serializes dates and other Pydantic types.
            cache_key = f"analysis_result:{analysis_result.document_id}"
            self.cache.set(cache_key, analysis_result.model_dump(), ex=3600)
            print(f"Updated full analysis with KG for {analysis_result.file_name} cached.")

        print(f"Knowledge Graph construction complete for {analysis_result.file_name}.")
        return analysis_result
