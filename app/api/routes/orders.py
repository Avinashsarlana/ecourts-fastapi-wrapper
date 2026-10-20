"""
API routes for Court Orders and Judgments searches.
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from app.schemas.response import OrderSearchResponse, ErrorResponse
from app.schemas.search import OrderSearchRequest
from app.services.case_search_service import case_search_service
from app.utils.exceptions import CaptchaRequiredException

router = APIRouter(prefix="/orders", tags=["Orders & Judgments"])


@router.post(
    "/search",
    response_model=OrderSearchResponse,
    summary="Search court orders",
    description="Searches for interim and final court orders passed by date, court number, or party name.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid search criteria or CAPTCHA"},
        410: {"model": ErrorResponse, "description": "Session expired"},
    },
)
def search_orders(payload: OrderSearchRequest) -> OrderSearchResponse:
    orders = case_search_service.search_orders(payload)
    return OrderSearchResponse(
        success=True,
        search_type="court_orders",
        query=payload.model_dump(),
        total_results=len(orders),
        results=orders,
    )


@router.get(
    "/search",
    response_model=OrderSearchResponse,
    summary="Search court orders (GET query parameters)",
    description="Retrieve orders by order_date with an active CAPTCHA session.",
)
def get_orders(
    order_date: Optional[str] = Query(None, description="Date of order in DD-MM-YYYY format"),
    court_number: Optional[str] = Query(None, description="Court number / room"),
    session_id: Optional[str] = Query(None, description="Active session ID"),
    captcha: Optional[str] = Query(None, description="Solved CAPTCHA text"),
) -> OrderSearchResponse:
    if not session_id or not captcha:
        raise CaptchaRequiredException(
            "eCourts requires CAPTCHA verification. Pass 'session_id' and 'captcha'."
        )

    req = OrderSearchRequest(
        session_id=session_id,
        captcha=captcha,
        state_code="MH",
        district_code="AU",
        court_complex_code="01",
        order_date=order_date,
        court_number=court_number,
    )
    orders = case_search_service.search_orders(req)
    return OrderSearchResponse(
        success=True,
        search_type="court_orders",
        query={"order_date": order_date, "court_number": court_number},
        total_results=len(orders),
        results=orders,
    )
