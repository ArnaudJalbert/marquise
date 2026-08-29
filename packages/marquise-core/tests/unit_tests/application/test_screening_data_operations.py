"""Regression tests for the screening data-operations use cases."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.queries.screening_data_operations import (
    ReconcileScreeningsCommand,
    ScreeningDataAuditQuery,
)
from marquise.application.readers import ScreeningReader
from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime


def _row(
    screening_id: str,
    showtime: datetime,
    *,
    ticket_url: str | None = "https://tickets.example/show",
) -> ScreeningReader.ScreeningData:
    return ScreeningReader.ScreeningData(
        id=screening_id,
        movie_id="movie-1",
        movie_title="Film",
        cinema_id="cinema-1",
        cinema_name="Cinema",
        showtime=showtime,
        ticket_url=ticket_url,
    )


@pytest.mark.asyncio
async def test_audit_reports_duplicate_stale_and_missing_ticket_findings() -> None:
    """Suspicious rows are reported without invoking any write collaborator."""
    reader = create_autospec(ScreeningReader, instance=True)
    now = datetime(2026, 8, 29, 12, tzinfo=UTC)
    reader.search = AsyncMock(
        return_value=type(
            "Page",
            (),
            {
                "items": [
                    _row("old", now - timedelta(hours=1), ticket_url=None),
                    _row("duplicate", now + timedelta(hours=1)),
                    _row("duplicate-2", now + timedelta(hours=1)),
                ],
                "total": 3,
            },
        )()
    )
    result = await ScreeningDataAuditQuery(reader, clock=lambda: now).execute(
        ScreeningDataAuditQuery.InputData()
    )
    codes = [finding.code for finding in result.findings]
    assert codes.count("stale_showtime") == 1
    assert codes.count("missing_ticket_url") == 1
    assert codes.count("duplicate_identity") == 1
    reader.search.assert_awaited_once_with(
        cinema_id=None, start_date=None, end_date=None, limit=None, offset=0
    )


@pytest.mark.asyncio
async def test_reconcile_dry_run_never_updates_repository() -> None:
    """The default reconciliation mode only validates and previews changes."""
    repository = create_autospec(ScreeningRepository, instance=True)
    repository.find_by_id = AsyncMock(
        return_value=Screening(
            id=ScreeningId(value="screening-1"),
            movie=Movie(id=MovieId(value="movie-1"), title="Film"),
            cinema=Cinema(id=CinemaId(value="cinema-1"), name="Cinema"),
            showtime=Showtime(value=datetime(2026, 8, 29, 14, tzinfo=UTC)),
            ticket_url=None,
        )
    )
    command = ReconcileScreeningsCommand(repository)
    result = await command.execute(
        ReconcileScreeningsCommand.InputData(
            corrections=(
                ReconcileScreeningsCommand.Correction(
                    screening_id="screening-1", ticket_url="https://tickets.example/new"
                ),
            ),
        )
    )
    assert result.changed_count == 0
    assert result.items[0].status == "dry-run"
    repository.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconcile_requires_apply_and_confirmation_for_writes() -> None:
    """Even an explicit apply flag cannot write without a separate confirmation."""
    repository = create_autospec(ScreeningRepository, instance=True)
    command = ReconcileScreeningsCommand(repository)
    with pytest.raises(ValueError, match="confirmation"):
        await command.execute(
            ReconcileScreeningsCommand.InputData(corrections=(), apply=True)
        )
