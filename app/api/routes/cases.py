"""
API routes for case search operations (CNR, Case Number, Party Name).
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, status
from app.schemas.response import CaseSearchResponse, ErrorResponse
from app.schemas.search import (
    CNRSearchRequest,
    CaseNumberSearchRequest,
    PartySearchRequest,
    AdvocateSearchRequest,
)
from app.services.case_search_service import case_search_service
from app.utils.cnr_validator import clean_cnr, is_valid_cnr
from app.utils.exceptions import InvalidCNRException

log = logging.getLogger(__name__)

router = APIRouter(prefix="/cases", tags=["Case Searches"])


@router.post(
    "/search",
    response_model=CaseSearchResponse,
    summary="Search case by CNR number",
    description="Submits a CNR search. 'session_id' and 'captcha' are optional.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid CNR or Invalid CAPTCHA"},
        404: {"model": ErrorResponse, "description": "Case record not found"},
        410: {"model": ErrorResponse, "description": "Session expired"},
    },
)
def search_case_by_cnr(payload: CNRSearchRequest) -> CaseSearchResponse:
    """Submit CNR search with optional session/captcha."""
    log.info("CNR received by FastAPI: '%s' (endpoint: POST /cases/search)", payload.cnr)
    cleaned = clean_cnr(payload.cnr)
    log.info("CNR after validation/normalization: '%s'", cleaned)
    if not is_valid_cnr(cleaned):
        raise InvalidCNRException(cnr=payload.cnr)
    payload.cnr = cleaned
    case = case_search_service.search_by_cnr(payload)
    return CaseSearchResponse(
        success=True,
        search_type="cnr",
        query={"cnr": cleaned},
        total_results=1,
        results=[case],
    )


@router.get(
    "/search",
    response_model=CaseSearchResponse,
    summary="Unified case search endpoint",
    description="Search cases via GET query parameters by providing the CNR number.",
)
def unified_case_search(
    cnr: Optional[str] = Query(None, description="16-character CNR number"),
    session_id: Optional[str] = Query(None, description="Optional session ID"),
    captcha: Optional[str] = Query(None, description="Optional CAPTCHA code"),
) -> CaseSearchResponse:
    """Unified GET endpoint for case searches."""
    log.info("CNR received by FastAPI: '%s' (endpoint: GET /cases/search)", cnr)
    if not cnr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one search criterion ('cnr') must be supplied.",
        )

    cleaned = clean_cnr(cnr)
    log.info("CNR after validation/normalization: '%s'", cleaned)
    if not is_valid_cnr(cleaned):
        raise InvalidCNRException(cnr=cnr)

    req = CNRSearchRequest(session_id=session_id, captcha=captcha, cnr=cleaned)
    case = case_search_service.search_by_cnr(req)
    return CaseSearchResponse(
        success=True,
        search_type="cnr",
        query={"cnr": cleaned},
        total_results=1,
        results=[case],
    )


@router.post(
    "/search/case-number",
    response_model=CaseSearchResponse,
    summary="Search case by Case Type, Number, and Year",
    description="Searches an establishment by specific case number and registration year.",
)
def search_by_case_number(payload: CaseNumberSearchRequest) -> CaseSearchResponse:
    results = case_search_service.search_by_case_number(payload)
    return CaseSearchResponse(
        success=True,
        search_type="case_number",
        query=payload.model_dump(),
        total_results=len(results),
        results=results,
    )


@router.post(
    "/search/party",
    response_model=CaseSearchResponse,
    summary="Search cases by Party Name",
    description="Searches cases where petitioner or respondent matches the given name.",
)
def search_by_party_name(payload: PartySearchRequest) -> CaseSearchResponse:
    results = case_search_service.search_by_party(payload)
    return CaseSearchResponse(
        success=True,
        search_type="party_name",
        query=payload.model_dump(),
        total_results=len(results),
        results=results,
    )
