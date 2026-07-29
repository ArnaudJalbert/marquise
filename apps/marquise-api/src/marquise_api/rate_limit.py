"""Shared per-IP rate limiter for the public API.

Extracted into its own module (rather than defined inline in ``app.py``) so
router modules can decorate individual endpoints with ``@limiter.limit(...)``
at import time, while ``create_app()`` still owns resetting its counters and
wiring it into each freshly built ``FastAPI`` app.

Endpoints registered directly on the ``FastAPI`` instance (e.g. ``/health``)
are covered by ``SlowAPIMiddleware`` and its ``default_limits``/``exempt``
mechanism. Endpoints registered via ``APIRouter.include_router()`` are *not*
visible to that middleware's route matching in the FastAPI version this
project pins, so those endpoints must be decorated explicitly with
``@limiter.limit(current_rate_limit)``.
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

#: Default per-IP rate limit, in slowapi's ``<count>/<period>`` string
#: syntax. Override via the ``MARQUISE_API_RATE_LIMIT`` env var.
DEFAULT_RATE_LIMIT: str = "3000/minute"


def current_rate_limit() -> str:
    """Return the configured per-IP rate limit.

    Read dynamically (rather than once at import time) so tests can adjust
    ``MARQUISE_API_RATE_LIMIT`` per case without reconstructing the limiter.

    Returns:
        The rate limit string, e.g. ``"60/minute"``.
    """
    return os.environ.get("MARQUISE_API_RATE_LIMIT", DEFAULT_RATE_LIMIT)


#: Module-level singleton so router-decorated endpoints and ``create_app()``
#: share the same limiter instance and in-memory counters. ``default_limits``
#: takes a callable so the configured limit can change (e.g. between tests)
#: without reconstructing the ``Limiter``.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[current_rate_limit],
    headers_enabled=True,
)
