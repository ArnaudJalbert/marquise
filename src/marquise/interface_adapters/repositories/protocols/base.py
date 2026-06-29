"""Shared gateway protocol primitives."""

from __future__ import annotations


class GatewayError(Exception):
    """Raised when a gateway operation fails at the data layer."""
