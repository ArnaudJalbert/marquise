"""Protocol for source adapters that translate domain entities to source params."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from marquise.domain.entities import Cinema


class SourceAdapter(Protocol):
    """Protocol for source adapter implementations.

    Each adapter wraps a ``ShowtimeSource`` (infrastructure scraper) and
    translates ``Cinema`` domain entities into the source-specific
    parameters.
    """

    async def fetch_showtimes(
        self,
        cinema: Cinema,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes from the underlying source.

        Args:
            cinema: The cinema entity to fetch showtimes for.
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).

        Returns:
            A list of raw dicts representing screening rows.
        """
        ...
