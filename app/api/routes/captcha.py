"""
API routes for CAPTCHA challenge generation and search session initiation.
Provides human-in-the-loop CAPTCHA challenges to client applications.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.response import SessionResponse, ErrorResponse
from app.clients.ecourts_client import ecourts_client
from app.services.session_service import session_service
from app.config.settings import settings

router = APIRouter(tags=["CAPTCHA & Sessions"])


@router.post(
    "/search/session",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new eCourts search session",
    description=(
        "Establishes a session with the official eCourts platform and returns a live "
        "CAPTCHA challenge (as a Base64 data URI). The client must present this image "
        "to a human user and include the solved text in the subsequent search request."
    ),
    responses={
        503: {"model": ErrorResponse, "description": "eCourts portal unreachable"},
        429: {"model": ErrorResponse, "description": "Rate limited by eCourts"},
    },
)
def create_search_session() -> SessionResponse:
    """Create a new search session with a CAPTCHA challenge."""
    cookies, captcha_bytes, meta = ecourts_client.initialize_session()
    session = session_service.create_session(
        cookies=cookies,
        captcha_image_bytes=captcha_bytes,
        extra_data=meta,
    )
    return SessionResponse(
        success=True,
        session_id=session.session_id,
        captcha_required=True,
        captcha_image=session.captcha_data_uri,
        expires_in_seconds=session.time_remaining,
    )


@router.get(
    "/search/session/{session_id}",
    response_model=SessionResponse,
    summary="Check session status and retrieve CAPTCHA challenge",
    description="Inspects an existing search session and returns its remaining time-to-live and challenge image.",
)
def get_session_status(session_id: str) -> SessionResponse:
    """Retrieve details and challenge image for an existing session."""
    session = session_service.get_session(session_id)
    return SessionResponse(
        success=True,
        session_id=session.session_id,
        captcha_required=True,
        captcha_image=session.captcha_data_uri,
        expires_in_seconds=session.time_remaining,
    )
