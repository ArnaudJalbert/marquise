"""Command use case: create screenings and shared import response DTOs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from marquise.application.exceptions import (
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
    ScreeningUpdateNotFoundError,
)
from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime

logger = logging.getLogger(__name__)

# ── Shared response DTOs for the import workflow ────────────────────────


@dataclass(frozen=True, slots=True)
class ImportedScreeningData:
    """Summary of a single imported or already-existing screening.

    Attributes:
        movie_title: The title of the movie.
        showtime: The showtime in ISO format.
        imported: True if newly created.
        rescheduled: True if an existing screening moved to a new showtime.
    """

    movie_title: str
    showtime: str
    imported: bool
    rescheduled: bool = False

    def __post_init__(self) -> None:
        if not self.movie_title.strip():
            raise ValueError("movie_title must not be empty")
        if not self.showtime.strip():
            raise ValueError("showtime must not be empty")


# ── Use case ────────────────────────────────────────────────────────────


class CreateScreeningsCommand:
    """Create or update screenings for every row in a batch.

    Each input row is self-contained (movie_id, cinema_id, etc.) — no
    lookups or external validation.  External_id collisions are skipped
    per-row rather than aborting the whole batch.
    """

    @dataclass(frozen=True, slots=True)
    class ScreeningInput:
        movie_id: str
        movie_title: str
        cinema_id: str
        cinema_name: str
        showtime: datetime
        external_id: str | None = None
        source_name: str | None = None
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

        def __post_init__(self) -> None:
            if not self.movie_id.strip():
                raise ValueError("movie_id must not be empty")
            if not self.movie_title.strip():
                raise ValueError("movie_title must not be empty")
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if not self.cinema_name.strip():
                raise ValueError("cinema_name must not be empty")
            if self.showtime.tzinfo is None:
                raise ValueError("showtime must be timezone-aware")

    @dataclass(frozen=True, slots=True)
    class InputData:
        screenings: tuple[CreateScreeningsCommand.ScreeningInput, ...]

    @dataclass(frozen=True, slots=True)
    class OutputData:
        screenings: tuple[ImportedScreeningData, ...]
        total_count: int
        imported_count: int
        updated_count: int
        skipped_count: int
        rescheduled_count: int = 0

        def __post_init__(self) -> None:
            if self.total_count < 0:
                raise ValueError("total_count must not be negative")
            if self.imported_count < 0:
                raise ValueError("imported_count must not be negative")
            if self.updated_count < 0:
                raise ValueError("updated_count must not be negative")
            if self.rescheduled_count < 0:
                raise ValueError("rescheduled_count must not be negative")
            if self.skipped_count < 0:
                raise ValueError("skipped_count must not be negative")

    def __init__(self, screening_repository: ScreeningRepository) -> None:
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        logger.info("Processing %d screening inputs", len(request.screenings))

        raw_results = await asyncio.gather(
            *[self._upsert_screening(row) for row in request.screenings],
            return_exceptions=True,
        )

        results: list[ImportedScreeningData] = []
        skipped_count = 0
        for row, outcome in zip(request.screenings, raw_results, strict=True):
            if isinstance(
                outcome,
                (ScreeningExternalIdConflictError, ScreeningUpdateNotFoundError),
            ):
                logger.warning(
                    "Skipped screening: cinema_id=%s movie_id=%s showtime=%s "
                    "external_id=%r reason=%s",
                    row.cinema_id,
                    row.movie_id,
                    row.showtime.isoformat(),
                    row.external_id,
                    outcome,
                )
                skipped_count += 1
                continue
            if isinstance(outcome, BaseException):
                raise outcome
            results.append(outcome)

        logger.info(
            "Screenings: %d created or updated, %d skipped",
            len(results),
            skipped_count,
        )

        return self.OutputData(
            screenings=tuple(results),
            total_count=len(results),
            imported_count=sum(1 for r in results if r.imported),
            updated_count=sum(
                1 for r in results if not r.imported and not r.rescheduled
            ),
            rescheduled_count=sum(1 for r in results if r.rescheduled),
            skipped_count=skipped_count,
        )

    async def _upsert_screening(
        self,
        row: ScreeningInput,
    ) -> ImportedScreeningData:
        movie = Movie(id=MovieId(value=row.movie_id), title=row.movie_title)
        cinema = Cinema(id=CinemaId(value=row.cinema_id), name=row.cinema_name)
        screening = Screening(
            id=ScreeningId(value=uuid4().hex),
            movie=movie,
            cinema=cinema,
            showtime=Showtime(value=row.showtime),
            external_id=row.external_id,
            source_name=row.source_name,
            ticket_url=row.ticket_url,
            room=row.room,
            language=row.language,
        )
        try:
            await self.screening_repository.save(screening)
        except ScreeningExternalIdConflictError as conflict:
            if row.external_id and row.source_name:
                try:
                    local_start, local_end = _local_day_bounds(row.showtime)
                    rescheduled = await self.screening_repository.reschedule(
                        screening,
                        source_name=row.source_name,
                        local_day_start=local_start,
                        local_day_end=local_end,
                    )
                except ScreeningAlreadyExistsError as target_conflict:
                    raise ScreeningExternalIdConflictError(
                        str(target_conflict)
                    ) from target_conflict
                if rescheduled is not None:
                    return ImportedScreeningData(
                        movie_title=row.movie_title,
                        showtime=row.showtime.isoformat(),
                        imported=False,
                        rescheduled=True,
                    )
            raise conflict
        except ScreeningAlreadyExistsError:
            updated = await self.screening_repository.update(screening)
            if updated is None:
                raise ScreeningUpdateNotFoundError(
                    f"Screening for cinema '{row.cinema_id}', movie "
                    f"'{row.movie_id}' at {row.showtime.isoformat()} "
                    f"was confirmed to exist on save but disappeared "
                    "before update."
                )
            return ImportedScreeningData(
                movie_title=row.movie_title,
                showtime=row.showtime.isoformat(),
                imported=False,
            )
        return ImportedScreeningData(
            movie_title=row.movie_title,
            showtime=row.showtime.isoformat(),
            imported=True,
        )


def _local_day_bounds(showtime: datetime) -> tuple[datetime, datetime]:
    """Return Montreal-local calendar-day bounds as UTC datetimes."""
    local_zone = ZoneInfo("America/Montreal")
    local_date = showtime.astimezone(local_zone).date()
    start = datetime.combine(local_date, time.min, tzinfo=local_zone).astimezone(UTC)
    return start, start + timedelta(days=1)
