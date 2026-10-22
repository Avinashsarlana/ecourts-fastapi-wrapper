"""
Custom exception hierarchy for the eCourts FastAPI wrapper.
Maps domain errors to structured error codes and HTTP status codes.
"""

from typing import Optional, Dict, Any


class ECourtsException(Exception):
    """Base exception for all eCourts wrapper errors."""
    def __init__(
        self,
        message: str,
        code: str = "SEARCH_FAILED",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class InvalidCNRException(ECourtsException):
    def __init__(self, message: str = "The supplied CNR number is invalid.", cnr: Optional[str] = None):
        super().__init__(
            message=message,
            code="INVALID_CNR",
            status_code=400,
            details={"cnr": cnr} if cnr else None,
        )


class CaptchaRequiredException(ECourtsException):
    def __init__(self, message: str = "CAPTCHA verification is required to proceed."):
        super().__init__(message=message, code="CAPTCHA_REQUIRED", status_code=428)


class CaptchaInvalidException(ECourtsException):
    def __init__(self, message: str = "The supplied CAPTCHA is invalid or has expired."):
        super().__init__(message=message, code="CAPTCHA_INVALID", status_code=400)


class SessionExpiredException(ECourtsException):
    def __init__(self, message: str = "The eCourts search session has expired. Please create a new session."):
        super().__init__(message=message, code="SESSION_EXPIRED", status_code=410)


class CaseNotFoundException(ECourtsException):
    def __init__(
        self,
        message: str = "No matching case data was found for the requested CNR.",
        cnr: Optional[str] = None,
    ):
        details = {"cnr": cnr} if cnr else None
        super().__init__(message=message, code="CASE_NOT_FOUND", status_code=404, details=details)
        self.cnr = cnr


class ECourtsUnavailableException(ECourtsException):
    def __init__(self, message: str = "Official eCourts portal is temporarily unavailable or unreachable."):
        super().__init__(message=message, code="ECOURTS_UNAVAILABLE", status_code=503)


class ECourtsTimeoutException(ECourtsException):
    def __init__(self, message: str = "Request to official eCourts portal timed out."):
        super().__init__(message=message, code="TIMEOUT", status_code=504)


class RateLimitedException(ECourtsException):
    def __init__(self, message: str = "Too many requests. Please wait before submitting again."):
        super().__init__(message=message, code="RATE_LIMITED", status_code=429)


class ParsingErrorException(ECourtsException):
    def __init__(self, message: str = "Failed to parse the response from eCourts."):
        super().__init__(message=message, code="PARSING_ERROR", status_code=502)


class UnsupportedSearchException(ECourtsException):
    def __init__(self, message: str = "The specified search criteria or combination is not supported."):
        super().__init__(message=message, code="UNSUPPORTED_SEARCH", status_code=400)
