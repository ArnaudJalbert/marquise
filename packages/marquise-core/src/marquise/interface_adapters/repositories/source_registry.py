"""Registry mapping source names to concrete SourceAdapter implementations.

Wired by the dependency injection container at startup.  Each adapter
translates ``Cinema`` entities into source-specific parameters.
"""

from __future__ import annotations

from datetime import UTC, datetime

from marquise.application.repositories import (
    MovieEnrichmentData,
    ShowtimeRow,
    SourceRegistryQuery,
)
from marquise.domain.entities import Cinema, SourceDefinition
from marquise.interface_adapters.repositories.source_adapters.base import (
    SourceAdapter,
)


def _parse_showtime(raw: str) -> datetime:
    """Parse a raw showtime string into a timezone-aware datetime.

    Accepts ISO 8601 format and ``YYYY-MM-DDTH:MM AM/PM`` format.

    Args:
        raw: The raw showtime string from a source.

    Returns:
        A timezone-aware datetime object (defaults to UTC if no tz).

    Raises:
        ValueError: If the string cannot be parsed.
    """
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        dt = datetime.strptime(raw, "%Y-%m-%dT%I:%M %p")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


class SourceRegistry(SourceRegistryQuery):
    """Maps source names to concrete ``SourceAdapter`` instances.

    Typical wiring in the DI container::

        registry = SourceRegistry()
        registry.register("cinemacinema", CinemaCinemaAdapter())
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, name: str, adapter: SourceAdapter) -> None:
        """Register a source adapter under a given name.

        Args:
            name: The unique source name (e.g. ``"cinemacinema"``).
            adapter: A ``SourceAdapter`` implementor.

        Raises:
            ValueError: If an adapter with the given ``name`` is already
                registered.
        """
        if name in self._adapters:
            raise ValueError(f"A source with name '{name}' is already registered")
        self._adapters[name] = adapter

    def list_available(self) -> list[str]:
        """Return the names of all registered sources.

        Returns:
            Unique machine names in registration order.
        """
        return list(self._adapters)

    async def fetch_showtimes(
        self,
        cinema: Cinema,
        source_definition: SourceDefinition,
        start_date: datetime,
        end_date: datetime,
    ) -> list[ShowtimeRow]:
        """Fetch showtimes from a registered source.

        Delegates to the registered adapter and maps the returned
        raw dicts to ``ShowtimeRow`` dataclasses, parsing the showtime
        strings into timezone-aware datetimes.

        Args:
            cinema: The cinema to fetch showtimes for.
            source_definition: The source definition identifying which
                registered source to use.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            A list of ``ShowtimeRow`` instances.

        Raises:
            KeyError: If no source is registered for the given
                ``source_definition`` name.
        """
        source_name = str(source_definition.name)
        adapter = self._adapters[source_name]
        raw_rows = await adapter.fetch_showtimes(
            cinema=cinema,
            start_date=start_date,
            end_date=end_date,
        )
        results: list[ShowtimeRow] = []
        for row in raw_rows:
            raw_showtime = row.get("showtime")
            if not raw_showtime:
                continue
            movie_title = row.get("movie_title") or ""
            if not movie_title.strip():
                continue
            results.append(
                ShowtimeRow(
                    movie_title=movie_title,
                    showtime=_parse_showtime(raw_showtime),
                    identifier=row.get("identifier"),
                    external_id=row.get("external_id"),
                    ticket_url=row.get("ticket_url"),
                    room=str(row["room"]) if row.get("room") is not None else None,
                    language=row.get("language"),
                )
            )
        return results

    async def fetch_movie_detail(
        self,
        source_name: str,
        identifier: str,
    ) -> MovieEnrichmentData | None:
        """Fetch enriched movie metadata from a registered source.

        Args:
            source_name: The name of the registered source.
            identifier: A source-specific identifier for the film.

        Returns:
            A ``MovieEnrichmentData`` if the source returns data, else
            ``None``.

        Raises:
            KeyError: If no source is registered for ``source_name``.
        """
        adapter = self._adapters[source_name]
        raw = await adapter.fetch_movie_detail(identifier=identifier)
        if not raw:
            return None
        return MovieEnrichmentData(
            description=raw.get("description"),
            directors=_to_tuple(raw.get("directors")),
            cast=_to_tuple(raw.get("cast")),
            duration_minutes=raw.get("duration_minutes"),
            release_year=raw.get("release_year"),
            origin_countries=_to_tuple(raw.get("origin_countries")),
            poster_url=raw.get("poster_url"),
            trailer_url=raw.get("trailer_url"),
            genres=_to_tuple(raw.get("genres")),
            rating=raw.get("rating"),
            original_title=raw.get("original_title"),
            identity_title=raw.get("identity_title"),
        )


def _to_tuple(value: object) -> tuple[str, ...] | None:
    """Convert a list-or-None to a tuple, or return ``None``."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        result = tuple(str(v).strip() for v in value if v)
        return result if result else None
    return None
