"""
API routes for CAPTCHA challenge resolution and search session initiation.
Returns the session ID and resolved CAPTCHA code directly.
"""

from fastapi import APIRouter, status
from app.schemas.response import SessionResponse, ErrorResponse
from app.clients.ecourts_client import ecourts_client
from app.services.session_service import session_service

router = APIRouter(tags=["CAPTCHA & Sessions"])


@router.post(
    "/search/session",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new eCourts search session",
    description=(
        "Establishes a session with the official eCourts platform and returns a session ID "
        "along with the resolved CAPTCHA code. No image data is generated."
    ),
    responses={
        503: {"model": ErrorResponse, "description": "eCourts portal unreachable"},
        429: {"model": ErrorResponse, "description": "Rate limited by eCourts"},
    },
)
def create_search_session() -> SessionResponse:
    """Create a new search session with the resolved CAPTCHA code."""
    cookies, captcha_code, meta = ecourts_client.initialize_session()
    session = session_service.create_session(
        cookies=cookies,
        captcha_code=captcha_code,
        extra_data=meta,
    )
    return SessionResponse(
        success=True,
        session_id=session.session_id,
        captcha=session.captcha_code,
        expires_in_seconds=session.time_remaining,
        captcha_required=False,
    )


@router.get(
    "/search/session/{session_id}",
    response_model=SessionResponse,
    summary="Check session status and retrieve CAPTCHA",
    description="Inspects an existing search session and returns its remaining time-to-live and CAPTCHA code.",
)
def get_session_status(session_id: str) -> SessionResponse:
    """Retrieve details and CAPTCHA code for an existing session."""
    session = session_service.get_session(session_id)
    return SessionResponse(
        success=True,
        session_id=session.session_id,
        captcha=session.captcha_code,
        expires_in_seconds=session.time_remaining,
        captcha_required=False,
    )


@router.delete(
    "/search/session/{session_id}",
    summary="Terminate an active search session",
    description="Closes an active session manually when batch searches are completed.",
)
def terminate_session(session_id: str):
    """Manually terminate and clean up an active search session."""
    session_service.remove_session(session_id)
    return {"success": True, "message": f"Session {session_id} successfully terminated."}
