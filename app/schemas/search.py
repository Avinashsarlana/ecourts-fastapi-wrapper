"""
Search request models and query parameter schemas for eCourts search modes.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from app.utils.cnr_validator import clean_cnr, is_valid_cnr


class SearchMode(str, Enum):
    CNR = "cnr"
    CASE_NUMBER = "case_number"
    PARTY_NAME = "party_name"
    ADVOCATE_NAME = "advocate_name"
    COURT_ORDERS = "court_orders"
    JUDGMENTS = "judgments"


class CaseStatusFilter(str, Enum):
    PENDING = "Pending"
    DISPOSED = "Disposed"
    BOTH = "Both"


class CNRSearchRequest(BaseModel):
    """Request payload for CNR-based case search."""
    cnr: str = Field(..., description="16-character alphanumeric CNR")
    session_id: Optional[str] = Field(None, description="Active session ID")
    captcha: Optional[str] = Field(None, max_length=15, description="CAPTCHA text code")

    @field_validator("cnr")
    @classmethod
    def validate_and_clean_cnr(cls, v: str) -> str:
        cleaned = clean_cnr(v)
        if not is_valid_cnr(cleaned):
            raise ValueError(f"Invalid CNR '{v}'. Must be a 16-character alphanumeric code.")
        return cleaned


class CaseNumberSearchRequest(BaseModel):
    """Request payload for Case Number search."""
    state_code: str = Field(..., description="Two-character State code")
    district_code: str = Field(..., description="District identifier")
    court_complex_code: str = Field(..., description="Court complex establishment identifier")
    case_type: str = Field(..., description="Case Type identifier or name")
    case_number: str = Field(..., description="Case Number")
    case_year: int = Field(..., ge=1900, le=2100, description="Registration year")
    session_id: Optional[str] = Field(None, description="Active session ID")
    captcha: Optional[str] = Field(None, description="CAPTCHA text code")


class PartySearchRequest(BaseModel):
    """Request payload for Party Name search."""
    state_code: str = Field(..., description="State code")
    district_code: str = Field(..., description="District code")
    court_complex_code: str = Field(..., description="Court complex code")
    party_name: str = Field(..., min_length=2, description="Petitioner or Respondent name")
    case_year: Optional[int] = Field(None, ge=1900, le=2100, description="Year of registration")
    status: CaseStatusFilter = Field(default=CaseStatusFilter.BOTH, description="Pending / Disposed filter")
    session_id: Optional[str] = Field(None, description="Active session ID")
    captcha: Optional[str] = Field(None, description="CAPTCHA text code")


class AdvocateSearchRequest(BaseModel):
    """Request payload for Advocate Name search."""
    state_code: str = Field(..., description="State code")
    district_code: str = Field(..., description="District code")
    court_complex_code: str = Field(..., description="Court complex code")
    advocate_name: str = Field(..., min_length=2, description="Advocate name")
    case_year: Optional[int] = Field(None, ge=1900, le=2100, description="Year of registration")
    session_id: Optional[str] = Field(None, description="Active session ID")
    captcha: Optional[str] = Field(None, description="CAPTCHA text code")


class OrderSearchRequest(BaseModel):
    """Request payload for Court Orders search."""
    state_code: str = Field(..., description="State code")
    district_code: str = Field(..., description="District code")
    court_complex_code: str = Field(..., description="Court complex code")
    order_date: Optional[str] = Field(None, description="Date of order")
    court_number: Optional[str] = Field(None, description="Court room number")
    party_name: Optional[str] = Field(None, description="Party name filter")
    session_id: Optional[str] = Field(None, description="Active session ID")
    captcha: Optional[str] = Field(None, description="CAPTCHA text code")
