"""
Standard API response schemas and normalized error envelopes.
"""

from typing import Generic, List, Optional, TypeVar, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.case import CaseDetails, OrderItem

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[Dict[str, Any]] = Field(None, description="Optional extra error context")


class ErrorResponse(BaseModel):
    """Standardized error envelope returned for all API exceptions."""
    success: bool = Field(default=False)
    error: ErrorDetail


class SessionResponse(BaseModel):
    """Session response providing the session ID and resolved CAPTCHA code."""
    success: bool = Field(default=True)
    session_id: str = Field(..., description="Unique search session ID")
    captcha: str = Field(..., description="CAPTCHA text code")
    expires_in_seconds: int = Field(default=600, description="Session time-to-live in seconds")
    captcha_required: bool = Field(default=False, description="Whether manual CAPTCHA solving is required")
    captcha_image: Optional[str] = Field(None, description="Optional image data")


class CaseSearchResponse(BaseModel):
    """Normalized response payload for case searches."""
    success: bool = Field(default=True)
    search_type: str = Field(..., description="Search mode executed")
    query: Dict[str, Any] = Field(..., description="Original search query parameters")
    total_results: int = Field(..., description="Total matching cases found")
    results: List[CaseDetails] = Field(default_factory=list, description="List of normalized case details")


class OrderSearchResponse(BaseModel):
    """Normalized response payload for court orders searches."""
    success: bool = Field(default=True)
    search_type: str = Field(default="court_orders")
    query: Dict[str, Any] = Field(..., description="Original query criteria")
    total_results: int = Field(..., description="Total matching orders found")
    results: List[OrderItem] = Field(default_factory=list, description="List of matched court orders")


class HealthResponse(BaseModel):
    status: str = Field(default="healthy")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="Current ISO timestamp")
    active_sessions: int = Field(..., description="Count of currently active search sessions")
