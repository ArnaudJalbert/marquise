"""Policy-free Screening storage for import and repository contract tests."""

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime

from marquise.application.exceptions.screening import ScreeningWriteConflictError
from marquise.application.repositories.page import Page
from marquise.application.repositories.screening_repository import ScreeningRepository
from marquise.domain.entities import Movie, Screening
from marquise.domain.value_objects import CinemaId, ScreeningId


class MemoryScreeningRepository(ScreeningRepository):
    """Store detached rows and check snapshots atomically without external I/O."""

    def __init__(self, rows: tuple[Screening, ...] = ()) -> None:
        """Initialize storage with detached copies of the supplied rows."""
        self.rows = {row.id: deepcopy(row) for row in rows}
        self.before_commit: Callable[[], None] | None = None

    async def read_import_candidates(
        self, incoming: Screening
    ) -> tuple[Screening, ...]:
        """Read rows matching the native key or target identity."""
        return tuple(
            deepcopy(row)
            for row in self.rows.values()
            if row.cinema.id == incoming.cinema.id
            and (
                (incoming.external_id and row.external_id == incoming.external_id)
                or (
                    row.movie.id == incoming.movie.id
                    and row.showtime.value.astimezone(UTC)
                    == incoming.showtime.value.astimezone(UTC)
                )
            )
        )

    async def commit_import(
        self,
        proposed: Screening,
        *,
        incoming: Screening,
        expected: tuple[Screening, ...],
    ) -> Screening:
        """Compare detached state and write one complete row without yielding."""
        if self.before_commit is not None:
            callback, self.before_commit = self.before_commit, None
            callback()
        current = await self.read_import_candidates(incoming)
        by_id = {row.id: row for row in current}
        for row in expected:
            if row.id in self.rows:
                by_id[row.id] = self.rows[row.id]
        if {identifier: _stored_fields(row) for identifier, row in by_id.items()} != {
            row.id: _stored_fields(row) for row in expected
        }:
            raise ScreeningWriteConflictError("Screening state changed")
        if proposed.id in self.rows and proposed.id not in {row.id for row in expected}:
            raise ScreeningWriteConflictError("Unexpected existing ID")
        if any(
            row.id != proposed.id
            and row.cinema.id == proposed.cinema.id
            and (
                (
                    row.movie.id == proposed.movie.id
                    and row.showtime.value.astimezone(UTC)
                    == proposed.showtime.value.astimezone(UTC)
                )
                or (proposed.external_id and row.external_id == proposed.external_id)
            )
            for row in self.rows.values()
        ):
            raise ScreeningWriteConflictError("Target arrived concurrently")
        self.rows[proposed.id] = deepcopy(proposed)
        return deepcopy(proposed)

    async def save(self, screening: Screening) -> Screening:
        """Unused by import tests."""
        raise NotImplementedError

    async def replace(
        self, screening: Screening, *, fields: frozenset[str]
    ) -> Screening:
        """Unused by import tests."""
        raise NotImplementedError

    async def delete(self, screening_id: ScreeningId) -> bool:
        """Unused by import tests."""
        return self.rows.pop(screening_id, None) is not None

    async def find_by_id(self, screening_id: ScreeningId) -> Screening:
        """Return a detached stored entity."""
        return deepcopy(self.rows[screening_id])

    async def find_distinct_movies_by_cinema(
        self,
        cinema_id: CinemaId,
        start_date: datetime,
        end_date: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[Movie]:
        """Unused by import tests."""
        raise NotImplementedError


def _stored_fields(row: Screening) -> tuple:
    """Compare persistence columns, excluding joined Movie and Cinema metadata."""
    return (
        row.id,
        row.movie.id,
        row.cinema.id,
        row.showtime.value.astimezone(UTC),
        row.external_id,
        row.source_name,
        row.ticket_url,
        row.room,
        row.language,
    )
