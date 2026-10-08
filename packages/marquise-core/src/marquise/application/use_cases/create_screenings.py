"""Command use case: create screenings and shared import response DTOs."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import uuid4

from marquise.application.exceptions import (
    ScreeningExternalIdConflictError,
    ScreeningUpdateNotFoundError,
)
from marquise.application.exceptions.screening import (
    ScreeningImportRetryExhaustedError,
    ScreeningWriteConflictError,
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

    Each input carries its Movie and Cinema identity. Persisted candidates
    determine updates and eligible moves. Native-key conflicts are skipped
    per row; stale writes reload and reevaluate with bounded retries.
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

        owners: dict[tuple[str, str], set[tuple[str, datetime, str | None]]] = {}
        for row in request.screenings:
            if row.external_id:
                owners.setdefault((row.cinema_id, row.external_id), set()).add(
                    (row.movie_id, row.showtime.astimezone(UTC), row.source_name)
                )
        ambiguous = {key for key, identities in owners.items() if len(identities) > 1}
        raw_results = await asyncio.gather(
            *[
                self._upsert_screening(
                    row, ambiguous=(row.cinema_id, row.external_id) in ambiguous
                )
                for row in request.screenings
            ],
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
        *,
        ambiguous: bool = False,
    ) -> ImportedScreeningData:
        if ambiguous:
            raise ScreeningExternalIdConflictError(
                "Ambiguous external-ID ownership in incoming batch"
            )
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
        previously_present = False
        for _ in range(3):
            state = await self.screening_repository.read_import_candidates(screening)
            if previously_present and not state:
                raise ScreeningUpdateNotFoundError(
                    "Screening disappeared or changed ownership before import commit"
                )
            previously_present = bool(state)
            owners = tuple(
                stored
                for stored in state
                if screening.external_id and stored.external_id == screening.external_id
            )
            targets = tuple(
                stored
                for stored in state
                if stored.movie.id == screening.movie.id
                and stored.cinema.id == screening.cinema.id
                and stored.showtime.value.astimezone(UTC)
                == screening.showtime.value.astimezone(UTC)
            )
            if len(owners) > 1 or len(targets) > 1:
                raise ScreeningExternalIdConflictError("Ambiguous ownership")
            target = targets[0] if targets else None
            owner = owners[0] if owners else None
            rescheduled = False
            if owner is not None and (target is None or owner.id != target.id):
                if target is not None:
                    raise ScreeningExternalIdConflictError(
                        "A screening already exists for the rescheduled identity"
                    )
                if not owner.can_reschedule_to(screening):
                    raise ScreeningExternalIdConflictError(
                        "Reschedule refused: Movie, native ID, source provenance "
                        "or Montreal calendar day differs"
                    )
                target = owner
                rescheduled = True
            proposed = screening
            if target is not None:
                if (
                    screening.source_name is not None
                    and target.source_name is not None
                    and screening.source_name != target.source_name
                ):
                    raise ScreeningExternalIdConflictError(
                        "Metadata update refused: source provenance differs"
                    )
                external_id = screening.external_id or target.external_id
                source_name = target.source_name
                if screening.external_id:
                    if screening.source_name is not None:
                        source_name = screening.source_name
                    elif screening.external_id != target.external_id:
                        source_name = None
                proposed = replace(
                    target,
                    showtime=screening.showtime,
                    external_id=external_id,
                    source_name=source_name,
                    ticket_url=screening.ticket_url
                    if screening.ticket_url is not None
                    else target.ticket_url,
                    room=screening.room if screening.room is not None else target.room,
                    language=screening.language
                    if screening.language is not None
                    else target.language,
                )
            else:
                proposed = replace(screening, external_id=screening.external_id or None)
            try:
                await self.screening_repository.commit_import(
                    proposed, incoming=screening, expected=state
                )
            except ScreeningWriteConflictError:
                continue
            return ImportedScreeningData(
                movie_title=row.movie_title,
                showtime=row.showtime.isoformat(),
                imported=target is None,
                rescheduled=rescheduled,
            )
        raise ScreeningImportRetryExhaustedError(
            "Screening import exhausted 3 checked-write attempts"
        )
