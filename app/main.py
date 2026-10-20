"""
Main FastAPI application entry point for the eCourts Services API Wrapper.
"""

from datetime import datetime, timezone
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from app.config.settings import settings
from app.utils.exceptions import ECourtsException
from app.schemas.response import ErrorResponse, ErrorDetail, HealthResponse
from app.api.routes import cases, captcha, orders
from app.services.session_service import session_service

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ecourts_api")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="""
# Official eCourts Services REST API Wrapper

A developer-friendly **REST API** that integrates with India's official **eCourts Services** platform (`services.ecourts.gov.in`).

### Key Capabilities:
* **Primary CNR Search (`/api/v1/cases/search`)**: Search case status, historical hearings, judges, and orders using the 16-character alphanumeric CNR.
* **Secondary Searches**: Case Number, Party Name, and Court Orders.
* **Human-in-the-Loop CAPTCHA Workflow (`/api/v1/search/session`)**: Compliant CAPTCHA challenge delivery to eliminate bot circumvention while enabling automated client pipelines.
* **Clean Structured Data**: Normalizes unstructured HTML tables into strongly-typed JSON models.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

# CORS middleware for frontend / browser integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(ECourtsException)
async def ecourts_exception_handler(request: Request, exc: ECourtsException):
    """Handle domain-specific eCourts exceptions."""
    log.warning("ECourtsException [%s]: %s (path: %s)", exc.code, exc.message, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic schema validation failures."""
    err_msgs = []
    sanitized_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        err_msgs.append(f"{loc}: {msg}")
        sanitized_errors.append({
            "type": err.get("type"),
            "loc": err.get("loc"),
            "msg": msg,
        })
    
    combined_msg = "; ".join(err_msgs)
    log.warning("Validation error on %s: %s", request.url.path, combined_msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="INVALID_REQUEST",
                message=combined_msg,
                details={"errors": sanitized_errors},
            ),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch unhandled unexpected exceptions without leaking internal secrets."""
    log.error("Unhandled internal server error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected internal server error occurred while processing the request.",
            ),
        ).model_dump(),
    )


# Register Routers
app.include_router(captcha.router, prefix=settings.API_PREFIX)
app.include_router(cases.router, prefix=settings.API_PREFIX)
app.include_router(orders.router, prefix=settings.API_PREFIX)


@app.get("/", tags=["System"])
def root_info():
    """Welcome and API documentation entry point."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "create_session": f"{settings.API_PREFIX}/search/session",
            "search_by_cnr": f"{settings.API_PREFIX}/cases/search",
            "search_orders": f"{settings.API_PREFIX}/orders/search",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Service health and session metric check."""
    return HealthResponse(
        status="healthy",
        version=settings.PROJECT_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        active_sessions=session_service.active_session_count,
    )
