# models/document_models.py (UPDATED - Added RAGResponse Model)

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any
from datetime import date

# --- Core Data Models for Document Processing ---

class DocumentInput(BaseModel):
    """
    Input model for the DocumentReaderAgent.
    Specifies the path to the legal document to be processed.
    """
    file_path: str = Field(description="Absolute or relative path to the legal document file.")

class Sentence(BaseModel):
    """
    Represents a single sentence within the document.
    Useful for precise referencing during extraction and RAG.
    """
    text: str = Field(description="The text content of the sentence.")
    index: int = Field(description="The 0-based index of the sentence within its paragraph.")
    # Consider adding 'paragraph_index' or 'section_id' for more context

class Paragraph(BaseModel):
    """
    Represents a paragraph within the document.
    """
    text: str = Field(description="The full text content of the paragraph.")
    index: int = Field(description="The 0-based index of the paragraph within the document.")
    sentences: List[Sentence] = Field(default_factory=list, description="List of sentences within this paragraph.")

class DocumentContent(BaseModel):
    """
    Output model for the DocumentReaderAgent.
    Contains the extracted plain text content and basic file metadata,
    now including structured paragraphs and sentences.
    """
    text_content: str = Field(description="Extracted plain text content of the document.")
    file_name: str = Field(description="Name of the original file (e.g., 'contract.pdf').")
    file_type: str = Field(description="Type of the original file (e.g., 'pdf', 'docx', 'txt').")
    paragraphs: List[Paragraph] = Field(default_factory=list, description="Document content segmented into structured paragraphs and sentences.")


# --- Data Models for Extracted Legal Entities (General) ---
# These are used across different extraction stages

class Party(BaseModel):
    """
    Represents a party involved in a legal document (e.g., Lessor, Lessee, Plaintiff).
    """
    name: str = Field(description="Full name of the party.")
    role: Optional[str] = Field(None, description="Role of the party (e.g., 'Lessor', 'Lessee', 'Plaintiff', 'Defendant').")
    address: Optional[str] = Field(None, description="Address of the party as mentioned in the document.")
    contact_info: Optional[str] = Field(None, description="Contact details (e.g., email, phone) if explicitly stated.")
    entity_type: Optional[Literal["individual", "company", "organization"]] = Field(
        None, description="Type of entity (e.g., individual, company)."
    )
    extracted_text: Optional[str] = Field(None, description="The exact text snippet from which this party was extracted.")

class DateClause(BaseModel):
    """
    Represents a date mentioned in a legal document, with its type and context.
    """
    date_type: str = Field(description="Type of date (e.g., 'Effective Date', 'Termination Date', 'Execution Date', 'Payment Due Date').")
    date_value: date = Field(description="The specific date in ISO-MM-DD format.")
    context: Optional[str] = Field(None, description="Sentence or phrase where the date was found.")
    related_to: Optional[str] = Field(None, description="What this date is related to (e.g., 'rent payment', 'contract term').")

class MonetaryValue(BaseModel):
    """
    Represents a monetary amount mentioned, including currency and reason.
    """
    amount: float = Field(description="The numerical monetary value.")
    currency: str = Field(description="The currency code (e.g., 'USD', 'INR', 'EUR').")
    context: Optional[str] = Field(None, description="Sentence or phrase where the monetary value was found.")
    reason: Optional[str] = Field(None, description="Reason for the payment/value (e.g., 'Rent', 'Fine', 'Compensation', 'Fee').")
    payment_frequency: Optional[Literal["monthly", "quarterly", "annually", "one-time"]] = Field(
        None, description="Frequency of payment, if applicable."
    )

class DefinedTerm(BaseModel):
    """
    Represents a defined term within the legal document, typically found in a definitions section.
    """
    term: str = Field(description="The defined term (e.g., 'Agreement', 'Services', 'Confidential Information').")
    definition: str = Field(description="The definition provided for the term.")
    location: Optional[str] = Field(None, description="Section or clause number where defined.")

# --- Comprehensive Extracted Entities Model (Targeted by LLM) ---
class ExtractedEntities(BaseModel):
    """
    Comprehensive structured output model for the full set of extracted information.
    This model will now be directly targeted by a single LLM call with Gemini 1.5 Flash.
    """
    document_type: Optional[str] = Field(None, description="The type of the legal document (e.g., 'Lease Agreement', 'NDA').")
    document_title: Optional[str] = Field(None, description="The title of the document.")
    document_effective_date: Optional[date] = Field(None, description="The primary effective date of the document.")
    parties: List[Party] = Field(default_factory=list, description="List of parties identified in the document.")
    jurisdiction: Optional[str] = Field(None, description="The primary governing jurisdiction of the document.")

    dates: List[DateClause] = Field(default_factory=list, description="List of important dates identified.")
    monetary_values: List[MonetaryValue] = Field(default_factory=list, description="List of monetary values identified.")
    defined_terms: List[DefinedTerm] = Field(default_factory=list, description="List of defined terms and their definitions.")

    indemnification_clauses: List[Dict] = Field(default_factory=list, description="List of indemnification clauses.")
    force_majeure_clauses: List[Dict] = Field(default_factory=list, description="List of force majeure clauses.")
    governing_law_clauses: List[Dict] = Field(default_factory=list, description="List of governing law clauses.")
    confidentiality_clauses: List[Dict] = Field(default_factory=list, description="List of confidentiality clauses.")
    termination_clauses: List[Dict] = Field(default_factory=list, description="List of termination clauses.")

    analysis_summary: Optional[str] = Field(None, description="A brief natural language summary of the document's key aspects.")


# --- Compliance Models ---

class ComplianceRule(BaseModel):
    """
    Defines a specific compliance rule or risk pattern to be checked.
    """
    rule_id: str = Field(description="Unique identifier for the compliance rule (e.g., 'GDPR-001', 'LEASE-005').")
    name: str = Field(description="Human-readable name of the rule (e.g., 'GDPR Data Minimization Principle', 'Lease Termination Notice Period').")
    description: str = Field(description="Detailed description of what the rule entails and why it's important.")
    check_criteria: str = Field(
        description="A natural language description or structured query fragment indicating how to check for compliance. "
                    "This will guide the LLM or a programmatic check."
    )
    severity_level: Literal["Critical", "High", "Medium", "Low", "Informational"] = Field(
        "Medium", description="Default severity if this rule is violated."
    )
    recommendation_template: str = Field(
        description="A template for a recommendation if the rule is violated (can be filled by LLM)."
    )

class ComplianceFinding(BaseModel):
    """
    Represents a specific finding related to compliance with a rule or standard.
    This is the output of a compliance check.
    """
    rule_id: str = Field(description="Identifier for the specific compliance rule being checked.")
    rule_description: str = Field(description="Human-readable description of the compliance rule.")
    is_compliant: bool = Field(description="True if compliant, False if non-compliant or potentially non-compliant.")
    finding_details: Optional[str] = Field(
        None, description="Detailed explanation of the compliance or non-compliance, including reasons."
    )
    relevant_text_snippets: List[str] = Field(
        default_factory=list, description="List of text snippets (clauses, sentences) directly relevant to this finding."
    )
    severity: Literal["Critical", "High", "Medium", "Low", "Informational"] = Field(
        "Informational", description="Severity of the finding."
    )
    recommendation: Optional[str] = Field(
        None, description="Suggested action or recommendation to achieve compliance or mitigate risk."
    )

# --- Knowledge Graph Models ---

class Node(BaseModel):
    """
    Represents an entity (node) in the Knowledge Graph.
    """
    id: str = Field(description="Unique identifier for the node (e.g., 'Document:abcd', 'Party:ABC_Corp').")
    type: str = Field(description="The type of entity (e.g., 'Document', 'Party', 'Clause', 'Date', 'MonetaryValue', 'Jurisdiction').")
    name: str = Field(description="The primary name or label for the entity.")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional properties of the entity.")

class Edge(BaseModel):
    """
    Represents a relationship (edge) between two nodes in the Knowledge Graph.
    """
    source_id: str = Field(description="The ID of the source node.")
    target_id: str = Field(description="The ID of the target node.")
    type: str = Field(description="The type of relationship (e.g., 'HAS_PARTY', 'GOVERNED_BY', 'REFERS_TO', 'HAS_DATE').")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional properties of the relationship.")

class KnowledgeGraph(BaseModel):
    """
    Represents a collection of nodes and edges forming a Knowledge Graph.
    """
    nodes: List[Node] = Field(default_factory=list, description="List of entities (nodes) in the graph.")
    edges: List[Edge] = Field(default_factory=list, description="List of relationships (edges) between nodes.")

# --- RAG Models ---
class RAGResponse(BaseModel):
    """
    Structured output for a Retrieval Augmented Generation (RAG) query.
    """
    answer: str = Field(description="The concise answer to the user's question.")
    confidence: Literal["High", "Medium", "Low"] = Field("Medium", description="Confidence level of the answer.")
    relevant_snippets: List[str] = Field(default_factory=list, description="List of relevant text snippets from the document or knowledge graph that support the answer.")
    source_nodes: List[str] = Field(default_factory=list, description="List of IDs of relevant knowledge graph nodes that contributed to the answer.")


# --- Overall Document Metadata and Analysis Result ---
class DocumentMetadata(BaseModel):
    """
    High-level metadata extracted from the legal document.
    """
    document_type: str = Field(description="Categorized type of the legal document (e.g., 'Lease Agreement', 'Service Contract', 'NDA', 'Policy').")
    title: Optional[str] = Field(None, description="Title of the document, if explicitly stated.")
    effective_date: Optional[date] = Field(None, description="Primary effective date of the document.")
    parties_summary: List[Party] = Field(default_factory=list, description="Summarized list of key parties involved.")
    jurisdiction: Optional[str] = Field(None, description="Primary governing law jurisdiction mentioned in the document.")
    version: Optional[str] = Field(None, description="Version or amendment status of the document.")


class DocumentAnalysisResult(BaseModel):
    """
    The comprehensive output of the legal document analysis.
    This model will be populated by various agents and represents the final, structured insights.
    """
    document_id: str = Field(description="Unique identifier generated for the analyzed document.")
    file_name: str = Field(description="Original file name of the document.")
    metadata: DocumentMetadata = Field(description="High-level metadata extracted from the document.")
    extracted_parties: List[Party] = Field(default_factory=list, description="All identified parties in the document.")
    extracted_dates: List[DateClause] = Field(default_factory=list, description="All identified dates in the document.")
    extracted_monetary_values: List[MonetaryValue] = Field(default_factory=list, description="All identified monetary values.")
    extracted_defined_terms: List[DefinedTerm] = Field(default_factory=list, description="All identified defined terms and their definitions.")

    extracted_clauses_summary: Dict[str, List[Dict]] = Field(
        default_factory=dict,
        description="A dictionary mapping clause types (e.g., 'Indemnification', 'ForceMajeure') to a list of their extracted details."
    )

    compliance_findings: List[ComplianceFinding] = Field(default_factory=list, description="List of all compliance findings.")
    analysis_summary: str = Field(description="A high-level natural language summary of the document and key findings.")

    full_text_content: str = Field(description="The complete preprocessed text content of the document.")
    paragraphs: List[Paragraph] = Field(default_factory=list, description="Document content segmented into paragraphs.")
    
    knowledge_graph: Optional[KnowledgeGraph] = Field(
        None, description="A structured knowledge graph representing entities and relationships within the document."
    )
    
# Note: The DocumentAnalysisResult model can be extended with more fields as needed for specific use cases.
# This model serves as the final output for the document analysis process, encapsulating all relevant information.