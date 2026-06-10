"""Import screenings from a cinema's showtime source into the local database."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import uuid4

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
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
        imported: True if newly created, False if already existed.
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
            updated_count: Number of existing screenings skipped.
        """

        cinema_id: str
        cinema_name: str
        source_name: str
        screenings: tuple[ImportedScreeningData, ...]
        total_count: int
        imported_count: int
        updated_count: int

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

        movie_lookup = await self._resolve_or_create_movies(rows)
        results = await asyncio.gather(
            *[self._upsert_screening(row, movie_lookup, cinema) for row in rows]
        )

        return self.OutputData(
            cinema_id=str(cinema.id),
            cinema_name=cinema.name,
            source_name=str(source_definition.name),
            screenings=tuple(results),
            total_count=len(results),
            imported_count=sum(1 for r in results if r.imported),
            updated_count=sum(1 for r in results if not r.imported),
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
            tzinfo=timezone.utc
        )
        end_dt = datetime.combine(request.end_date, datetime.max.time()).replace(
            tzinfo=timezone.utc
        )

        return cinema, assignment.source, start_dt, end_dt

    async def _resolve_or_create_movies(
        self,
        rows: list[ShowtimeRow],
    ) -> dict[str, Movie]:
        """Look up movies by title in parallel, creating missing ones.

        Args:
            rows: The showtime rows from the source.

        Returns:
            A mapping of movie title to Movie entity.
        """
        titles = [row.movie_title for row in rows]
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

        if missing_titles:
            new_movies = [
                Movie(
                    id=MovieId(value=uuid4().hex),
                    title=title,
                    release_date=None,
                    directors=None,
                    cast=None,
                )
                for title in missing_titles
            ]
            saved_movies = await asyncio.gather(
                *[self.movie_repository.save(m) for m in new_movies]
            )
            for movie in saved_movies:
                movie_lookup[movie.title] = movie

        return movie_lookup

    async def _upsert_screening(
        self,
        row: ShowtimeRow,
        movie_lookup: dict[str, Movie],
        cinema: Cinema,
    ) -> ImportedScreeningData:
        """Create or upsert a single screening from a showtime row.

        Args:
            row: The showtime row to persist.
            movie_lookup: Mapping of movie title to Movie entity.
            cinema: The cinema hosting the screening.

        Returns:
            A summary of the imported screening.
        """
        movie = movie_lookup[row.movie_title]
        screening = Screening(
            id=ScreeningId(value=uuid4().hex),
            movie=movie,
            cinema=cinema,
            showtime=Showtime(value=row.showtime),
        )
        screening, was_inserted = await self.screening_repository.save(screening)
        return ImportedScreeningData(
            movie_title=row.movie_title,
            showtime=row.showtime.strftime("%Y-%m-%d %H:%M"),
            imported=was_inserted,
        )
