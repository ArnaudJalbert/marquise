"""Query use case: fetch screenings and movie data from a cinema's source."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    MovieEnrichmentData,
    SourceRegistryQuery,
)
from marquise.domain.value_objects import CinemaId

logger = logging.getLogger(__name__)


class FetchScreeningsFromSourceQuery:
    """Resolve a cinema and its assigned source, fetch showtimes and movie details."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        cinema_id: str
        start_date: date
        end_date: date
        enrichment_concurrency: int = 8

        def __post_init__(self) -> None:
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if self.start_date > self.end_date:
                raise ValueError("start_date must not be after end_date")
            if self.enrichment_concurrency < 1:
                raise ValueError("enrichment_concurrency must be positive")

    @dataclass(frozen=True, slots=True)
    class FetchedMovieData:
        title: str
        identifier: str | None = None
        description: str | None = None
        directors: tuple[str, ...] | None = None
        cast: tuple[str, ...] | None = None
        duration_minutes: int | None = None
        release_year: int | None = None
        poster_url: str | None = None
        trailer_url: str | None = None
        genres: tuple[str, ...] | None = None
        original_title: str | None = None
        rating: str | None = None
        origin_countries: tuple[str, ...] | None = None

    @dataclass(frozen=True, slots=True)
    class FetchedScreeningData:
        movie_title: str
        showtime: datetime
        external_id: str | None = None
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

        def __post_init__(self) -> None:
            if not self.movie_title.strip():
                raise ValueError("movie_title must not be empty")
            if self.showtime.tzinfo is None:
                raise ValueError("showtime must be timezone-aware")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        cinema_id: str
        cinema_name: str
        source_name: str
        movies: tuple[FetchScreeningsFromSourceQuery.FetchedMovieData, ...]
        screenings: tuple[FetchScreeningsFromSourceQuery.FetchedScreeningData, ...]

    def __init__(
        self,
        cinema_repository: CinemaRepository,
        assignment_repository: CinemaSourceAssignmentRepository,
        source_registry: SourceRegistryQuery,
    ) -> None:
        self.cinema_repository = cinema_repository
        self.assignment_repository = assignment_repository
        self.source_registry = source_registry

    async def execute(self, request: InputData) -> OutputData:
        cinema_id = CinemaId(value=request.cinema_id)
        cinema = await self.cinema_repository.find_by_id(cinema_id)
        if cinema is None:
            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )

        assignment = await self.assignment_repository.find_by_cinema_id(cinema_id)
        if assignment is None:
            raise CinemaSourceAssignmentNotFoundError(
                f"No source assigned to cinema '{request.cinema_id}'"
            )

        source_name = str(assignment.source.name)

        start_dt = datetime.combine(request.start_date, datetime.min.time()).replace(
            tzinfo=UTC
        )
        end_dt = datetime.combine(request.end_date, datetime.max.time()).replace(
            tzinfo=UTC
        )

        raw_rows = await self.source_registry.fetch_showtimes(
            cinema=cinema,
            source_definition=assignment.source,
            start_date=start_dt,
            end_date=end_dt,
        )
        logger.info(
            "Fetched %d showtime rows for cinema '%s' (%s) from source '%s'",
            len(raw_rows),
            cinema.name,
            request.cinema_id,
            source_name,
        )

        unique_identifiers: list[str] = list(
            dict.fromkeys(r.identifier for r in raw_rows if r.identifier)
        )

        detail_map: dict[str, MovieEnrichmentData] = {}
        if unique_identifiers:
            raw_details = await _fetch_movie_details(
                self.source_registry,
                source_name,
                unique_identifiers,
                request.enrichment_concurrency,
            )
            for ident, detail in zip(unique_identifiers, raw_details):
                if isinstance(detail, MovieEnrichmentData):
                    detail_map[ident] = detail
                elif isinstance(detail, BaseException):
                    logger.warning(
                        "Failed movie detail fetch for '%s' on '%s': %s",
                        ident,
                        source_name,
                        detail,
                    )
            logger.info(
                "Fetched details for %d/%d unique identifiers",
                len(detail_map),
                len(unique_identifiers),
            )

        seen_titles: dict[str, str | None] = {}
        for row in raw_rows:
            norm = _normalize_title(row.movie_title)
            if norm not in seen_titles:
                seen_titles[norm] = row.identifier

        movie_list: list[FetchScreeningsFromSourceQuery.FetchedMovieData] = []
        for title, ident in seen_titles.items():
            detail = detail_map.get(ident) if ident else None
            movie_list.append(
                self.FetchedMovieData(
                    title=title,
                    identifier=ident,
                    description=detail.description if detail else None,
                    directors=detail.directors if detail else None,
                    cast=detail.cast if detail else None,
                    duration_minutes=detail.duration_minutes if detail else None,
                    release_year=detail.release_year if detail else None,
                    poster_url=detail.poster_url if detail else None,
                    trailer_url=detail.trailer_url if detail else None,
                    genres=detail.genres if detail else None,
                    original_title=detail.original_title if detail else None,
                    rating=detail.rating if detail else None,
                    origin_countries=detail.origin_countries if detail else None,
                )
            )

        logger.info(
            "Produced %d unique movies and %d screenings for cinema '%s'",
            len(movie_list),
            len(raw_rows),
            request.cinema_id,
        )

        return self.OutputData(
            cinema_id=str(cinema.id),
            cinema_name=cinema.name,
            source_name=source_name,
            movies=tuple(movie_list),
            screenings=tuple(
                self.FetchedScreeningData(
                    movie_title=r.movie_title,
                    showtime=r.showtime,
                    external_id=r.external_id,
                    ticket_url=r.ticket_url,
                    room=r.room,
                    language=r.language,
                )
                for r in raw_rows
            ),
        )


async def _fetch_movie_detail(
    source_registry: SourceRegistryQuery,
    source_name: str,
    identifier: str,
    semaphore: asyncio.Semaphore,
) -> MovieEnrichmentData | Exception:
    """Fetch one detail row while preserving predictable source failure isolation."""
    async with semaphore:
        try:
            detail = await source_registry.fetch_movie_detail(source_name, identifier)
        except (OSError, TimeoutError) as exc:
            return exc
        return (
            detail
            if isinstance(detail, MovieEnrichmentData)
            else ValueError("source returned an invalid enrichment result")
        )


async def _fetch_movie_details(
    source_registry: SourceRegistryQuery,
    source_name: str,
    identifiers: list[str],
    concurrency: int,
) -> list[MovieEnrichmentData | Exception]:
    """Fetch movie details concurrently with an explicit upper bound."""
    semaphore = asyncio.Semaphore(concurrency)
    return list(
        await asyncio.gather(
            *(
                _fetch_movie_detail(source_registry, source_name, identifier, semaphore)
                for identifier in identifiers
            )
        )
    )


def _normalize_title(title: str) -> str:
    """Strip and collapse internal whitespace in a scraped movie title."""
    return " ".join(title.strip().split())
