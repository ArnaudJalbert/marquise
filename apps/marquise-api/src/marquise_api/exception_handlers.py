"""Global FastAPI exception handlers for a consistent error envelope.

Centralizes error-to-response mapping so routers stay free of per-endpoint
try/except boilerplate. Registered once in ``create_app()``.
"""

from __future__ import annotations

import logging

from fastapi import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from marquise import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    ApplicationError,
    AuthAdministrationError,
    AuthenticationError,
    AuthenticationServiceUnavailableError,
    AuthorizationError,
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    MovieNotFoundError,
    ScreeningAlreadyExistsError,
    ScreeningNotFoundError,
    SelfDemotionError,
    SourceAlreadyExistsError,
    SourceNotFoundError,
    TooManyMovieIdsError,
)

logger = logging.getLogger(__name__)

#: Maps each concrete ApplicationError subclass to its (status_code,
#: error_code) pair. Every subclass in application/exceptions/__init__.py's
#: __all__ should have an explicit entry here; a subclass with no entry
#: falls back to the constants below.
_APPLICATION_ERROR_MAPPING: dict[type[ApplicationError], tuple[int, str]] = {
    AccountAlreadyExistsError: (409, "conflict"),
    AccountNotFoundError: (404, "not_found"),
    AuthAdministrationError: (502, "auth_administration_error"),
    AuthenticationError: (401, "authentication_error"),
    AuthenticationServiceUnavailableError: (503, "service_unavailable"),
    AuthorizationError: (403, "authorization_error"),
    SelfDemotionError: (409, "conflict"),
    CinemaNotFoundError: (404, "not_found"),
    MovieNotFoundError: (404, "not_found"),
    ScreeningNotFoundError: (404, "not_found"),
    SourceNotFoundError: (404, "not_found"),
    CinemaSourceAssignmentNotFoundError: (404, "not_found"),
    TooManyMovieIdsError: (422, "invalid_input"),
    CinemaAlreadyExistsError: (409, "conflict"),
    ScreeningAlreadyExistsError: (409, "conflict"),
    SourceAlreadyExistsError: (409, "conflict"),
    CinemaSourceAssignmentAlreadyExistsError: (409, "conflict"),
    # A generated ID collision is an internal retry condition, not a
    # client-facing conflict -- see CinemaIdAlreadyExistsError's docstring.
    CinemaIdAlreadyExistsError: (500, "internal_server_error"),
}
_DEFAULT_APPLICATION_ERROR_STATUS = 400
_DEFAULT_APPLICATION_ERROR_CODE = "application_error"

_HTTP_ERROR_CODES: dict[int, str] = {
    401: "authentication_error",
    403: "authorization_error",
    404: "not_found",
    405: "method_not_allowed",
    503: "service_unavailable",
}


async def http_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Map framework HTTP errors to the standard JSON envelope."""
    assert isinstance(exc, StarletteHTTPException)
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        {
            "detail": detail,
            "error_code": _HTTP_ERROR_CODES.get(exc.status_code, "http_error"),
            "request_id": request_id,
        },
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def application_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Map a known ApplicationError subclass to a consistent JSON envelope.

    Args:
        request: The incoming request (required by FastAPI's handler
            signature, unused here).
        exc: The application-layer exception raised by a use case.

    Returns:
        A JSONResponse with ``{"detail": ..., "error_code": ...}`` and the
        status code looked up from ``_APPLICATION_ERROR_MAPPING``.
    """
    assert isinstance(exc, ApplicationError)
    status_code, error_code = _APPLICATION_ERROR_MAPPING.get(
        type(exc), (_DEFAULT_APPLICATION_ERROR_STATUS, _DEFAULT_APPLICATION_ERROR_CODE)
    )
    request_id = getattr(request.state, "request_id", None)
    if status_code >= 500:
        logger.exception(
            "Unexpected application error",
            exc_info=exc,
            extra={"request_id": request_id},
        )
    return JSONResponse(
        {"detail": str(exc), "error_code": error_code, "request_id": request_id},
        status_code=status_code,
    )


async def value_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Map an unvalidated ValueError raised by a use case to a 422 response.

    Args:
        request: The incoming request (unused).
        exc: The ValueError raised by application code (e.g. bad date range).

    Returns:
        A JSONResponse with the standard error envelope and status 422.
    """
    assert isinstance(exc, ValueError)
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        {
            "detail": str(exc),
            "error_code": "invalid_input",
            "request_id": request_id,
        },
        status_code=422,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log an unhandled exception and return a generic 500 without leaking internals.

    Args:
        request: The incoming request that triggered the exception (used
            only for the log line's context).
        exc: The unexpected, otherwise-uncaught exception.

    Returns:
        A JSONResponse naming the exception's class (for debuggability)
        but never its message/args, which could contain internal details
        such as SQL fragments or connection info.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled exception processing request %s",
        request.url.path,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        {
            "detail": (
                f"An unexpected {type(exc).__name__} occurred while "
                "processing the request."
            ),
            "error_code": "internal_server_error",
            "request_id": request_id,
        },
        status_code=500,
    )
