"""Protocol for showtime source gateways.

Each source (cinemacinema, cineplex, etc.) defines ``fetch_showtimes`` with
its own parameter signature.  This protocol enforces that every source has
the method, without dictating the parameters.
"""

from __future__ import annotations

from typing import Any, Protocol


class ShowtimeSource(Protocol):
    """Protocol for showtime source gateway implementations.

    Every source must implement ``fetch_showtimes``, but each source defines
    its own parameter signature (e.g. ``cinema_name: str`` for cinemacinema,
    ``venue_id: str`` for cineplex).  Callers must know the concrete type and
    pass the appropriate arguments.
    """

    async def fetch_showtimes(
        self,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> list[dict[str, Any]]:
        """Fetch showtimes.

        Args:
            *args: Source-specific positional arguments.
            **kwargs: Source-specific keyword arguments.

        Returns:
            A list of plain dicts, each representing a screening row.
        """
        ...

    async def fetch_movie_detail(
        self,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> dict[str, Any] | None:
        """Fetch enriched movie metadata.

        Args:
            *args: Source-specific positional arguments.
            **kwargs: Source-specific keyword arguments.

        Returns:
            A dict of movie metadata if found, or ``None``.
        """
        ...
