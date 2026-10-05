"""Best-effort invalidation of the instance-local public response cache."""

import logging

from fastapi import Request
from fastapi_cache import FastAPICache

logger = logging.getLogger(__name__)


async def invalidate_public_cache(request: Request) -> None:
    """Clear all public responses only after the mutation use case succeeds."""
    try:
        await FastAPICache.clear()
    except Exception:
        # The write has committed. Never retry it or expose exception/body/token data.
        logger.error(
            "Public response cache invalidation failed",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.scope["route"].path,
            },
        )
