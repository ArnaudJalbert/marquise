"""Plain data source used by a movie identity search adapter."""

from __future__ import annotations

from typing import Protocol


class MovieSearchError(Exception):
    """A movie metadata lookup failed or returned invalid data."""


class MovieSearchSource(Protocol):
    """Fetch a provider response without mapping it to application types."""

    async def search(self, title: str, year: int | None) -> dict:
        """Return the provider response as plain data."""
        ...
