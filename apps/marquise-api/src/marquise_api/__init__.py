"""Marquise read-only REST API.

A FastAPI application serving cinema showtime data aggregated by
``marquise-core``.
"""

from marquise_api.app import create_app

__all__ = ["create_app"]
