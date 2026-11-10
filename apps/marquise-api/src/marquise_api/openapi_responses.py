"""Reusable OpenAPI ``responses=`` fragments for error documentation.

Centralizes the ``{"model": ErrorResponse, "description": ...}`` boilerplate
that would otherwise be repeated across every router endpoint. Each
constant/function returns a dict shaped for FastAPI's per-route
``responses=`` parameter, keyed by status code.
"""

from __future__ import annotations

from typing import Any

from marquise_api.schemas import ErrorResponse

#: Human-readable description shown in /docs for each documented status
#: code, keyed by status code. Extend when a new status code is documented
#: on any endpoint.
_DESCRIPTIONS: dict[int, str] = {
    404: "Requested resource not found (`not_found`).",
    422: "Request body, query, or path validation failed (`invalid_input`).",
    429: "Too many requests — the per-IP rate limit was exceeded.",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Build a FastAPI ``responses=`` dict for the given error status codes.

    Args:
        status_codes: Status codes to document, e.g. ``404, 422, 429``.
            Each must have an entry in ``_DESCRIPTIONS``.

    Returns:
        A dict suitable for a route's ``responses=`` kwarg, mapping each
        status code to ``{"model": ErrorResponse, "description": ...}``.

    Raises:
        KeyError: If a status code has no registered description.
    """
    return {
        code: {"model": ErrorResponse, "description": _DESCRIPTIONS[code]}
        for code in status_codes
    }
