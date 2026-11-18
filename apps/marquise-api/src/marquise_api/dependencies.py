"""Factory-backed FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from marquise import MarquiseFactory


def get_factory(request: Request) -> MarquiseFactory:
    """Return initialized factory stored on application state."""
    return request.app.state.factory
