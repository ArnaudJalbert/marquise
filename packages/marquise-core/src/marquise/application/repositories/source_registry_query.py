"""Application-layer interfaces for querying source gateways.

Defines contracts for fetching showtimes and enriching movie data from
external sources.  The concrete ``SourceRegistry`` in
``interface_adapters/repositories/`` implements these interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from marquise.domain.entities import Cinema, SourceDefinition


@dataclass(frozen=True, slots=True)
class ShowtimeRow:
    """A single showtime row returned by a source.

    Attributes:
        movie_title: The title of the movie.
        showtime: The showtime as a timezone-aware datetime.
        identifier: Source-specific identifier for fetching movie details
            (e.g. a slug or a film detail URL).  ``None`` if unavailable.
        external_id: Source-native deduplication key (e.g. a representation
            ID or ticket URL).  ``None`` if unavailable.
        ticket_url: Direct link to purchase tickets.  ``None`` if unavailable.
        room: Room or auditorium name.  ``None`` if unavailable.
        language: Language or subtitle version.  ``None`` if unavailable.
    """

    movie_title: str
    showtime: datetime
    identifier: str | None = None
    external_id: str | None = None
    ticket_url: str | None = None
    room: str | None = None
    language: str | None = None

    def __post_init__(self) -> None:
        """Validate the row at the scraper boundary.

        Raises:
            ValueError: If ``movie_title`` is empty or whitespace-only, or if
                ``showtime`` is a naive (timezone-unaware) datetime.
        """
        if not self.movie_title.strip():
            raise ValueError("movie_title must not be empty")
        if self.showtime.tzinfo is None:
            raise ValueError("showtime must be timezone-aware")


@dataclass(frozen=True, slots=True)
class MovieEnrichmentData:
    """Enriched movie metadata fetched from an external source.

    Attributes:
        description: Plot synopsis (plain text).  ``None`` if unavailable.
        directors: Tuple of director names.  ``None`` if unavailable.
        cast: Tuple of cast member names.  ``None`` if unavailable.
        duration_minutes: Runtime in minutes.  ``None`` if unavailable.
        release_year: Theatrical release year.  ``None`` if unavailable.
        origin_countries: Tuple of production country names.
            ``None`` if unavailable.
        poster_url: URL to the movie poster image.  ``None`` if unavailable.
        trailer_url: URL to the movie trailer.  ``None`` if unavailable.
        genres: Tuple of genre names.  ``None`` if unavailable.
        rating: Content rating string (e.g. ``"18+"``).  ``None`` if unavailable.
        original_title: Original title in the native language.
            ``None`` if unavailable.
        identity_title: Film title from the linked detail page, without a
            source event label when the page distinguishes the two.
    """

    description: str | None = None
    directors: tuple[str, ...] | None = None
    cast: tuple[str, ...] | None = None
    duration_minutes: int | None = None
    release_year: int | None = None
    origin_countries: tuple[str, ...] | None = None
    poster_url: str | None = None
    trailer_url: str | None = None
    genres: tuple[str, ...] | None = None
    rating: str | None = None
    original_title: str | None = None
    identity_title: str | None = None


class SourceRegistryQuery(ABC):
    """Interface for listing available showtime source gateways."""

    @abstractmethod
    def list_available(self) -> list[str]:
        """Return the names of all registered sources.

        Returns:
            Unique machine names (e.g. ``"cinemacinema"``).
        """
        ...

    @abstractmethod
    async def fetch_showtimes(
        self,
        cinema: Cinema,
        source_definition: SourceDefinition,
        start_date: datetime,
        end_date: datetime,
    ) -> list[ShowtimeRow]:
        """Fetch showtimes from a registered source.

        Args:
            cinema: The cinema to fetch showtimes for.
            source_definition: The source definition identifying which
                registered source to use.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            A list of ``ShowtimeRow`` dataclass instances.

        Raises:
            KeyError: If no source is registered for the given
                ``source_definition`` name.
        """
        ...

    @abstractmethod
    async def fetch_movie_detail(
        self,
        source_name: str,
        identifier: str,
    ) -> MovieEnrichmentData | None:
        """Fetch enriched movie metadata from a registered source.

        Args:
            source_name: The name of the registered source to query.
            identifier: A source-specific identifier (e.g. a slug or a
                film detail URL) obtained from a ``ShowtimeRow``.

        Returns:
            A ``MovieEnrichmentData`` instance if available, or ``None``
            if the source does not support enrichment or no data is found.

        Raises:
            KeyError: If no source is registered for ``source_name``.
        """
        ...
