"""Shared gateway protocol primitives."""

from __future__ import annotations

from dataclasses import dataclass


class GatewayError(Exception):
    """Raised when a gateway operation fails at the data layer."""


@dataclass(frozen=True, slots=True)
class GatewayPage:
    """A page of raw rows plus the total count matching the filter.

    Attributes:
        rows: The page of rows as plain dicts, already LIMIT/OFFSET-applied
            (or the full result set if no limit was requested).
        total: Total number of rows matching the filter, ignoring
            limit/offset.
    """

    rows: list[dict]
    total: int
