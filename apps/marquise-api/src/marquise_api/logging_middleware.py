"""Structured JSON request logging for the public API.

Environment variables
----------------------
MARQUISE_API_LOG_LEVEL
    Root logger level (default: ``INFO``).

Every request is assigned a request ID (honoring an incoming
``X-Request-ID`` header when present, e.g. behind a gateway/proxy that
already assigns trace IDs, otherwise a generated ``uuid4``). The ID is
echoed back via the ``X-Request-ID`` response header and stored on
``request.state.request_id`` so ``exception_handlers.py`` can thread it
into error response bodies, correlating a failure's response with its log
line.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

#: Default root logger level. Override via the MARQUISE_API_LOG_LEVEL env var.
DEFAULT_LOG_LEVEL: str = "INFO"

#: LogRecord attributes that are already emitted explicitly or are internal
#: bookkeeping — excluded when scanning a record for caller-supplied `extra`
#: fields to fold into the JSON payload.
_STANDARD_LOG_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
)


class JsonFormatter(logging.Formatter):
    """Formats each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string with timestamp, level, logger name,
            message, any caller-supplied ``extra`` fields, and (for
            exception logs) the formatted traceback.
        """
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None) -> None:
    """Install a JSON-formatted handler on the root logger.

    Clears any handlers already installed on the root logger first, so
    calling this repeatedly (e.g. once per ``create_app()`` in tests) does
    not stack duplicate handlers.

    Args:
        level: Root logger level name. Defaults to the
            ``MARQUISE_API_LOG_LEVEL`` env var, or ``DEFAULT_LOG_LEVEL``.
    """
    resolved_level = level or os.environ.get(
        "MARQUISE_API_LOG_LEVEL", DEFAULT_LOG_LEVEL
    )

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(resolved_level)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs one structured JSON line per request and tags it with a request ID."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Time the request, log its outcome, and stamp it with a request ID.

        Args:
            request: The incoming request.
            call_next: The next handler in the middleware chain.

        Returns:
            The response produced by ``call_next``, with an added
            ``X-Request-ID`` header.
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        response.headers["X-Request-ID"] = request_id
        return response
