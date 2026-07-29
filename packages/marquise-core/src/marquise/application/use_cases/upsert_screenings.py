"""Command use case: upsert screenings for a batch of showtime rows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from marquise.application.exceptions import ScreeningAlreadyExistsError
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
)
from marquise.application.use_cases.ensure_movies_exist import _normalize_title
from marquise.application.use_cases.import_screenings import ImportedScreeningData
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime


class UpsertScreeningsCommand:
    """Create or update a screening for each showtime row.

    Fans out the per-row upserts in parallel. Screenings whose external_id
    collides with a different existing screening are skipped (counted in
    ``skipped_count``) rather than aborting the whole batch — a source can
    report the same source-native ID against a different showtime (e.g. a
    rescheduled or reused session ID). Any other error aborts the batch.
    """

    @dataclass(frozen=True, slots=True)
    class ScreeningRow:
        """A single showtime row to persist as a screening.

        Attributes:
            movie_title: The title of the movie.
            showtime: The showtime as a timezone-aware datetime.
            external_id: Source-native deduplication key.
            ticket_url: Direct link to purchase tickets.
            room: Room or auditorium name.
            language: Language or subtitle version.
        """

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
    class InputData:
        """Input data for upserting screenings.

        Attributes:
            rows: The showtime rows to persist.
            cinema_id: The ID of the cinema hosting the screenings.
            movie_lookup: Mapping of normalized movie title to movie ID (hex).
        """

        rows: tuple[UpsertScreeningsCommand.ScreeningRow, ...]
        cinema_id: str
        movie_lookup: dict[str, str]

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after upserting screenings.

        Attributes:
            screenings: Summaries of the screenings processed.
            total_count: Total number of screenings processed.
            imported_count: Number of new screenings created.
            updated_count: Number of existing screenings found and updated.
            skipped_count: Number of screenings skipped because their
                external_id collided with a different existing screening.
        """

        screenings: tuple[ImportedScreeningData, ...]
        total_count: int
        imported_count: int
        updated_count: int
        skipped_count: int

        def __post_init__(self) -> None:
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
        screening_repository: ScreeningRepository,
        cinema_repository: CinemaRepository,
        movie_repository: MovieRepository,
    ) -> None:
        self.screening_repository = screening_repository
        self.cinema_repository = cinema_repository
        self.movie_repository = movie_repository

    async def execute(self, request: InputData) -> OutputData:
        """Upsert every showtime row, tallying imported/updated/skipped counts.

        Args:
            request: The rows, cinema ID, and movie lookup to persist.

        Returns:
            Output data with per-row summaries and aggregate counts.

        Raises:
            BaseException: Any non-collision error raised while persisting a row.
        """
        cinema, movie_map = await asyncio.gather(
            self.cinema_repository.find_by_id(CinemaId(value=request.cinema_id)),
            self._resolve_movies(request.movie_lookup),
        )
        if cinema is None:
            from marquise.application.exceptions import CinemaNotFoundError

            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )

        raw_results = await asyncio.gather(
            *[self._upsert_screening(row, movie_map, cinema) for row in request.rows],
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
            screenings=tuple(results),
            total_count=len(results),
            imported_count=sum(1 for r in results if r.imported),
            updated_count=sum(1 for r in results if not r.imported),
            skipped_count=skipped_count,
        )

    async def _resolve_movies(
        self,
        movie_lookup: dict[str, str],
    ) -> dict[str, Movie]:
        """Fetch full Movie entities by ID from the lookup.

        Args:
            movie_lookup: Mapping of normalized movie title to movie ID (hex).

        Returns:
            Mapping of normalized movie title to Movie entity.
        """
        if not movie_lookup:
            return {}

        unique_ids = list(set(movie_lookup.values()))
        fetched = await asyncio.gather(
            *[
                self.movie_repository.find_by_id(MovieId(value=mid))
                for mid in unique_ids
            ]
        )
        id_to_movie: dict[str, Movie] = {
            mid: movie for mid, movie in zip(unique_ids, fetched) if movie is not None
        }
        return {
            title: id_to_movie[mid]
            for title, mid in movie_lookup.items()
            if mid in id_to_movie
        }

    async def _upsert_screening(
        self,
        row: ScreeningRow,
        movie_map: dict[str, Movie],
        cinema: Cinema,
    ) -> ImportedScreeningData:
        """Create or update a single screening from a showtime row.

        Args:
            row: The showtime row to persist.
            movie_map: Mapping of normalized movie title to Movie entity.
            cinema: The cinema hosting the screening.

        Returns:
            A summary of the imported screening.
        """
        movie = movie_map[_normalize_title(row.movie_title)]
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
