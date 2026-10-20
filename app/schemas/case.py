"""
Domain schemas for eCourts Case Details, History, Orders, and Documents.
Designed to normalize raw HTML / tabular data from official eCourts into structured Pydantic models.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CaseHistoryItem(BaseModel):
    """A single court hearing or business entry in the case timeline."""
    hearing_date: Optional[str] = Field(None, description="Date of the hearing (DD-MM-YYYY)")
    business_on_date: Optional[str] = Field(None, description="Date when business was recorded")
    purpose_of_hearing: Optional[str] = Field(None, description="Purpose or stage of hearing")
    judge: Optional[str] = Field(None, description="Presiding judge / bench name")


class OrderItem(BaseModel):
    """An interim or final order recorded for the case."""
    order_number: Optional[str] = Field(None, description="Order / Decree number")
    order_date: Optional[str] = Field(None, description="Date the order was passed (DD-MM-YYYY)")
    order_type: Optional[str] = Field(None, description="Order or Judgment type")
    order_details: Optional[str] = Field(None, description="Brief summary or description of the order")
    document_url: Optional[str] = Field(None, description="Public download URL for the order PDF if available")


class DocumentItem(BaseModel):
    """Public document / exhibit / judgment metadata."""
    title: str = Field(..., description="Document title or description")
    document_type: str = Field(default="PDF", description="Format or document category")
    date: Optional[str] = Field(None, description="Document publication or filing date")
    url: Optional[str] = Field(None, description="Publicly accessible URL to the document")


class ActSectionItem(BaseModel):
    """Underlying statutory Act and Section applied to the case."""
    act: Optional[str] = Field(None, description="Statute or Act name (e.g. Indian Penal Code)")
    section: Optional[str] = Field(None, description="Applicable section number(s)")


class SubordinateCourtInfo(BaseModel):
    """Trial court / lower court details in case of appeals."""
    court_name: Optional[str] = Field(None, description="Name of the lower court")
    case_number: Optional[str] = Field(None, description="Case number in the trial court")
    decision_date: Optional[str] = Field(None, description="Decision date of the trial court")


class CaseDetails(BaseModel):
    """Normalized complete representation of an Indian eCourts case record."""
    cnr: str = Field(..., description="16-character unique Case Number Record")
    case_number: Optional[str] = Field(None, description="Registration / Case number")
    case_type: Optional[str] = Field(None, description="Type of case (e.g. Civil Suit, Criminal Revision)")
    court: Optional[str] = Field(None, description="Name of the court or establishment")
    court_complex: Optional[str] = Field(None, description="Court complex / location")
    district: Optional[str] = Field(None, description="District name")
    state: Optional[str] = Field(None, description="State name")
    
    # Parties & Advocates
    petitioner: Optional[str] = Field(None, description="Petitioner / Appellant / Complainant name")
    petitioner_advocate: Optional[str] = Field(None, description="Petitioner's advocate name")
    respondent: Optional[str] = Field(None, description="Respondent / Defendant name")
    respondent_advocate: Optional[str] = Field(None, description="Respondent's advocate name")

    # Dates & Status
    filing_number: Optional[str] = Field(None, description="Initial filing number")
    filing_date: Optional[str] = Field(None, description="Date of initial filing")
    registration_number: Optional[str] = Field(None, description="Official registration number")
    registration_date: Optional[str] = Field(None, description="Date of case registration")
    status: Optional[str] = Field(None, description="Current case status (e.g. PENDING, DISPOSED)")
    first_hearing_date: Optional[str] = Field(None, description="First hearing date")
    next_hearing_date: Optional[str] = Field(None, description="Next upcoming hearing date")
    disposal_date: Optional[str] = Field(None, description="Date of final disposal if closed")
    disposal_nature: Optional[str] = Field(None, description="Nature of disposal (e.g. Disposed, Dismissed)")
    stage_of_case: Optional[str] = Field(None, description="Current stage in proceeding")

    # Linked Information
    acts: List[ActSectionItem] = Field(default_factory=list, description="Associated Acts and Sections")
    subordinate_court: Optional[SubordinateCourtInfo] = Field(None, description="Lower court appeal info")
    case_history: List[CaseHistoryItem] = Field(default_factory=list, description="Historical timeline of hearings")
    orders: List[OrderItem] = Field(default_factory=list, description="List of issued orders / judgments")
    documents: List[DocumentItem] = Field(default_factory=list, description="Publicly available case documents")
