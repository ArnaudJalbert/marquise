"""Import screenings from a cinema's showtime source into the local database."""

from __future__ import annotations

import asyncio
import dataclasses
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import uuid4

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
    ScreeningAlreadyExistsError,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    MovieEnrichmentData,
    MovieRepository,
    ScreeningRepository,
    SourceRegistryQuery,
)
from marquise.application.repositories.source_registry_query import ShowtimeRow
from marquise.domain.entities import Cinema, Movie, Screening, SourceDefinition
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)


@dataclass(frozen=True, slots=True)
class ImportedScreeningData:
    """Summary of a single imported or already-existing screening.

    Attributes:
        movie_title: The title of the movie.
        showtime: The showtime in ISO format.
        imported: True if newly created, False if already existed and updated in place.
    """

    movie_title: str
    showtime: str
    imported: bool

    def __post_init__(self) -> None:
        if not self.movie_title.strip():
            raise ValueError("movie_title must not be empty")
        if not self.showtime.strip():
            raise ValueError("showtime must not be empty")


class ImportScreeningsUseCase:
    """Import screenings from a cinema's assigned showtime source.

    Fetches showtimes from the external source, creates or updates
    Movie entities as needed, and upserts Screening entities into
    the local database.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for importing screenings.

        Attributes:
            cinema_id: The ID of the cinema to import screenings for.
            start_date: Earliest date to import (inclusive).
            end_date: Latest date to import (inclusive).
        """

        cinema_id: str
        start_date: date
        end_date: date

        def __post_init__(self) -> None:
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if self.start_date > self.end_date:
                raise ValueError("start_date must not be after end_date")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after importing screenings.

        Attributes:
            cinema_id: The ID of the cinema.
            cinema_name: The display name of the cinema.
            source_name: The name of the source used.
            screenings: List of imported/existing screening summaries.
            total_count: Total number of screenings processed.
            imported_count: Number of new screenings created.
            updated_count: Number of existing screenings found and updated in place.
            skipped_count: Number of screenings skipped because their
                external_id collided with a different existing screening.
        """

        cinema_id: str
        cinema_name: str
        source_name: str
        screenings: tuple[ImportedScreeningData, ...]
        total_count: int
        imported_count: int
        updated_count: int
        skipped_count: int = 0

        def __post_init__(self) -> None:
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if not self.cinema_name.strip():
                raise ValueError("cinema_name must not be empty")
            if not self.source_name.strip():
                raise ValueError("source_name must not be empty")
            if self.total_count < 0:
                raise ValueError("total_count must not be negative")
            if self.imported_count < 0:
                raise ValueError("imported_count must not be negative")
            if self.updated_count < 0:
                raise ValueError("updated_count must not be negative")
            if self.skipped_count < 0:
                raise ValueError("skipped_count must not be negative")

    def __init__(
        self,
        cinema_repository: CinemaRepository,
        assignment_repository: CinemaSourceAssignmentRepository,
        source_registry: SourceRegistryQuery,
        movie_repository: MovieRepository,
        screening_repository: ScreeningRepository,
    ) -> None:
        self.cinema_repository = cinema_repository
        self.assignment_repository = assignment_repository
        self.source_registry = source_registry
        self.movie_repository = movie_repository
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """Import screenings from a cinema's showtime source.

        Screenings whose external_id collides with a different existing
        screening are skipped (counted in ``skipped_count``) rather than
        aborting the whole import — a source can report the same
        source-native ID against a different showtime (e.g. a rescheduled
        or reused session ID).

        Args:
            request: The input data specifying which cinema and date range.

        Returns:
            A summary of all screenings processed.

        Raises:
            CinemaNotFoundError: If the cinema does not exist.
            CinemaSourceAssignmentNotFoundError: If the cinema has no
                assigned source.
            ValueError: If fetching or parsing showtimes fails.
        """
        (
            cinema,
            source_definition,
            start_dt,
            end_dt,
        ) = await self._resolve_cinema_and_source(request)

        rows = await self.source_registry.fetch_showtimes(
            cinema=cinema,
            source_definition=source_definition,
            start_date=start_dt,
            end_date=end_dt,
        )

        movie_lookup = await self._resolve_or_create_movies(
            rows, str(source_definition.name)
        )
        raw_results = await asyncio.gather(
            *[self._upsert_screening(row, movie_lookup, cinema) for row in rows],
            return_exceptions=True,
        )

        results: list[ImportedScreeningData] = []
        skipped_count = 0
        for outcome in raw_results:
            if isinstance(outcome, ScreeningAlreadyExistsError):
                skipped_count += 1
                continue
            if isinstance(outcome, BaseException):
                raise outcome
            results.append(outcome)

        return self.OutputData(
            cinema_id=str(cinema.id),
            cinema_name=cinema.name,
            source_name=str(source_definition.name),
            screenings=tuple(results),
            total_count=len(results),
            imported_count=sum(1 for r in results if r.imported),
            updated_count=sum(1 for r in results if not r.imported),
            skipped_count=skipped_count,
        )

    async def _resolve_cinema_and_source(
        self,
        request: InputData,
    ) -> tuple[Cinema, SourceDefinition, datetime, datetime]:
        """Fetch cinema, assignment, and source definition.

        Args:
            request: The input data.

        Returns:
            A tuple of (cinema, source_definition, start_dt, end_dt).

        Raises:
            CinemaNotFoundError: If the cinema does not exist.
            CinemaSourceAssignmentNotFoundError: If no source is assigned.
            ValueError: If the source definition is not found.
        """
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

        start_dt = datetime.combine(request.start_date, datetime.min.time()).replace(
            tzinfo=UTC
        )
        end_dt = datetime.combine(request.end_date, datetime.max.time()).replace(
            tzinfo=UTC
        )

        return cinema, assignment.source, start_dt, end_dt

    async def _resolve_or_create_movies(
        self,
        rows: list[ShowtimeRow],
        source_name: str,
    ) -> dict[str, Movie]:
        """Look up movies by title in parallel, creating and enriching missing ones.

        Enriches movies with metadata from the source when available. Titles
        are normalized (whitespace-collapsed) before being used as lookup or
        dict keys so that scraper noise like a trailing space doesn't create
        a duplicate movie; the repository additionally matches case-insensitively.

        Args:
            rows: The showtime rows from the source.
            source_name: The name of the source (used for enrichment queries).

        Returns:
            A mapping of normalized movie title to Movie entity.
        """
        titles = [_normalize_title(row.movie_title) for row in rows]
        found_movies = await asyncio.gather(
            *[self.movie_repository.find_by_title(t) for t in titles]
        )

        movie_lookup: dict[str, Movie] = {}
        missing_titles: list[str] = []
        for title, movie in zip(titles, found_movies):
            if movie is not None:
                movie_lookup[title] = movie
            else:
                missing_titles.append(title)

        # Map each unique title to its identifier for enrichment
        title_to_identifier: dict[str, str | None] = {}
        for row in rows:
            normalized_title = _normalize_title(row.movie_title)
            if normalized_title not in title_to_identifier:
                title_to_identifier[normalized_title] = row.identifier

        # -- New movies --
        new_movies_by_title: dict[str, Movie] = {}
        for title in missing_titles:
            new_movies_by_title[title] = Movie(
                id=MovieId(value=uuid4().hex),
                title=title,
            )

        # -- Build (title, identifier) pairs for movies that can be enriched --
        enrich_pairs: list[tuple[str, str]] = []
        for title in missing_titles:
            identifier = title_to_identifier.get(title)
            if identifier:
                enrich_pairs.append((title, identifier))

        for title, movie in movie_lookup.items():
            identifier = title_to_identifier.get(title)
            if identifier is not None and _needs_enrichment(movie):
                enrich_pairs.append((title, identifier))

        enriched_existing: set[str] = set()
        if enrich_pairs:
            enrich_results = await asyncio.gather(
                *[
                    self.source_registry.fetch_movie_detail(source_name, ident)
                    for _, ident in enrich_pairs
                ],
                return_exceptions=True,
            )

            for (title, _), enrichment in zip(enrich_pairs, enrich_results):
                if not isinstance(enrichment, MovieEnrichmentData):
                    continue
                if title in new_movies_by_title:
                    new_movies_by_title[title] = _apply_enrichment(
                        new_movies_by_title[title], enrichment
                    )
                else:
                    movie_lookup[title] = _apply_enrichment(
                        movie_lookup[title], enrichment
                    )
                    enriched_existing.add(title)

        movies_to_save_keys: list[str] = [
            *new_movies_by_title.keys(),
            *enriched_existing,
        ]
        movies_to_save: list[Movie] = [
            *new_movies_by_title.values(),
            *[movie_lookup[t] for t in enriched_existing],
        ]

        # -- Save all enriched movies in parallel --
        if movies_to_save:
            saved_movies = await asyncio.gather(
                *[self.movie_repository.save(m) for m in movies_to_save]
            )
            # Re-key by the lookup key used above (not the saved entity's own
            # title) since find_by_title matches case-insensitively: the
            # returned title may differ in case from the key rows in this
            # batch are indexed under, and re-keying by it would orphan them.
            for key, movie in zip(movies_to_save_keys, saved_movies):
                movie_lookup[key] = movie

        return movie_lookup

    async def _upsert_screening(
        self,
        row: ShowtimeRow,
        movie_lookup: dict[str, Movie],
        cinema: Cinema,
    ) -> ImportedScreeningData:
        """Create or update a single screening from a showtime row.

        Args:
            row: The showtime row to persist.
            movie_lookup: Mapping of normalized movie title to Movie entity.
            cinema: The cinema hosting the screening.

        Returns:
            A summary of the imported screening.
        """
        movie = movie_lookup[_normalize_title(row.movie_title)]
        screening = Screening(
            id=ScreeningId(value=uuid4().hex),
            movie=movie,
            cinema=cinema,
            showtime=Showtime(value=row.showtime),
            external_id=row.external_id,
            ticket_url=row.ticket_url,
            room=row.room,
            language=row.language,
        )
        screening, was_inserted = await self.screening_repository.save(screening)
        if not was_inserted:
            await self.screening_repository.update(screening)
        return ImportedScreeningData(
            movie_title=row.movie_title,
            showtime=row.showtime.strftime("%Y-%m-%d %H:%M"),
            imported=was_inserted,
        )


def _normalize_title(title: str) -> str:
    """Strip and collapse internal whitespace in a scraped movie title.

    Different scrapers (or the same scraper on different days) can emit the
    same title with a stray leading/trailing space or doubled internal
    spaces; normalizing keeps those from being treated as distinct movies.
    Case is left untouched — case-insensitive matching happens at the
    repository layer.
    """
    return " ".join(title.strip().split())


# Optional Movie fields that can be populated from enrichment data.
_ENRICHABLE_FIELDS = (
    "description",
    "directors",
    "cast",
    "duration_minutes",
    "release_year",
    "poster_url",
    "trailer_url",
    "genres",
    "original_title",
    "rating",
    "origin_countries",
)


def _needs_enrichment(movie: Movie) -> bool:
    """Check whether a movie has any null optional fields."""
    return any(getattr(movie, field) is None for field in _ENRICHABLE_FIELDS)


def _apply_enrichment(
    movie: Movie,
    enrichment: MovieEnrichmentData,
) -> Movie:
    """Return a new Movie with null fields populated from enrichment data."""
    updates = {
        field: getattr(enrichment, field)
        for field in _ENRICHABLE_FIELDS
        if getattr(movie, field) is None and getattr(enrichment, field) is not None
    }
    return dataclasses.replace(movie, **updates)
