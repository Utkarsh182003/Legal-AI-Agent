# models/legal_clauses.py

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- Specific Legal Clause Models ---
# These models define the structure for different types of clauses found in legal documents.

class IndemnificationClause(BaseModel):
    """
    Represents an indemnification clause, detailing who indemnifies whom for what.
    """
    clause_text: str = Field(description="The full text of the indemnification clause.")
    indemnifying_party_names: List[str] = Field(
        default_factory=list, description="List of names of parties responsible for indemnifying."
    )
    indemnified_party_names: List[str] = Field(
        default_factory=list, description="List of names of parties to be indemnified."
    )
    scope: Optional[str] = Field(
        None, description="The scope of indemnification (e.g., 'all losses', 'direct damages only', 'excluding negligence')."
    )
    exceptions: Optional[List[str]] = Field(
        default_factory=list, description="Any exceptions or limitations to the indemnification."
    )
    trigger_events: Optional[List[str]] = Field(
        default_factory=list, description="Events that trigger the indemnification obligation."
    )

class ForceMajeureClause(BaseModel):
    """
    Represents a Force Majeure clause, detailing events that excuse performance.
    """
    clause_text: str = Field(description="The full text of the Force Majeure clause.")
    defined_events: List[str] = Field(
        default_factory=list, description="List of events considered Force Majeure (e.g., 'acts of God', 'war', 'epidemics')."
    )
    notice_period_days: Optional[int] = Field(
        None, description="Number of days for notice after a Force Majeure event, if specified."
    )
    effect_on_obligations: str = Field(
        description="How obligations are affected (e.g., 'suspended', 'excused', 'terminated')."
    )
    mitigation_requirement: Optional[bool] = Field(
        None, description="True if a party is required to mitigate the effects of the event."
    )

class GoverningLawClause(BaseModel):
    """
    Represents a Governing Law clause, specifying the jurisdiction whose laws apply.
    """
    clause_text: str = Field(description="The full text of the Governing Law clause.")
    jurisdiction: str = Field(description="The specific governing law jurisdiction (e.g., 'State of New York', 'laws of England and Wales').")
    country: Optional[str] = Field(None, description="The country associated with the jurisdiction.")

class ConfidentialityClause(BaseModel):
    """
    Represents a confidentiality clause, defining confidential information and obligations.
    """
    clause_text: str = Field(description="The full text of the Confidentiality clause.")
    defined_confidential_info: Optional[List[str]] = Field(
        default_factory=list, description="Examples or categories of information deemed confidential."
    )
    obligated_parties: Optional[List[str]] = Field(
        default_factory=list, description="Parties obligated to maintain confidentiality."
    )
    disclosure_exceptions: Optional[List[str]] = Field(
        default_factory=list, description="Conditions under which disclosure is permitted (e.g., 'court order')."
    )
    duration_years: Optional[int] = Field(
        None, description="Duration of confidentiality obligation in years, if specified."
    )

class TerminationClause(BaseModel):
    """
    Represents a termination clause, detailing conditions for contract termination.
    """
    clause_text: str = Field(description="The full text of the Termination clause.")
    termination_for_cause_events: Optional[List[str]] = Field(
        default_factory=list, description="Events allowing termination for cause (e.g., 'material breach', 'insolvency')."
    )
    termination_for_convenience_allowed: Optional[bool] = Field(
        None, description="True if termination for convenience is allowed."
    )
    notice_period_days: Optional[int] = Field(
        None, description="Notice period for termination in days, if specified."
    )
    post_termination_obligations: Optional[List[str]] = Field(
        default_factory=list, description="Obligations that survive termination (e.g., 'confidentiality', 'indemnification')."
    )

# Add more clause types as needed
# e.g., WarrantyClause, LimitationOfLiabilityClause, IntellectualPropertyClause, DisputeResolutionClause
