"""Tests for the bulk import orchestration (`marquise import all`)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
)
from marquise.infrastructure.cli.import_commands import run_import_all


def _make_container(
    cinemas: list[SimpleNamespace], import_side_effect: object
) -> MagicMock:
    """Build a fake DI container with mocked cinema/source controllers."""
    container = MagicMock()
    container.cinema_controller.list = AsyncMock(
        return_value=SimpleNamespace(cinemas=cinemas)
    )
    container.source_controller.import_screenings = AsyncMock(
        side_effect=import_side_effect
    )
    return container


@pytest.mark.asyncio
async def test_run_import_all_imports_each_cinema() -> None:
    """Every cinema with a source is imported and its counts captured."""
    cinemas = [
        SimpleNamespace(id="cin-1", name="Cinema One"),
        SimpleNamespace(id="cin-2", name="Cinema Two"),
    ]
    outputs = [
        SimpleNamespace(imported_count=3, updated_count=1),
        SimpleNamespace(imported_count=0, updated_count=5),
    ]
    container = _make_container(cinemas, import_side_effect=outputs)

    results = await run_import_all(container, days=7)

    assert [r.status for r in results] == ["imported", "imported"]
    assert results[0].imported_count == 3
    assert results[1].updated_count == 5
    assert container.source_controller.import_screenings.await_count == 2


@pytest.mark.asyncio
async def test_run_import_all_skips_cinema_without_source() -> None:
    """Cinemas without a source assignment are skipped, not failed."""
    cinemas = [SimpleNamespace(id="cin-1", name="Cinema One")]
    container = _make_container(
        cinemas,
        import_side_effect=CinemaSourceAssignmentNotFoundError("none"),
    )

    results = await run_import_all(container, days=7)

    assert len(results) == 1
    assert results[0].status == "skipped"
    assert results[0].detail == "no source assigned"


@pytest.mark.asyncio
async def test_run_import_all_records_failure_without_aborting() -> None:
    """A per-cinema failure is recorded and does not stop later cinemas."""
    cinemas = [
        SimpleNamespace(id="cin-1", name="Cinema One"),
        SimpleNamespace(id="cin-2", name="Cinema Two"),
    ]
    container = _make_container(
        cinemas,
        import_side_effect=[
            CinemaNotFoundError("gone"),
            SimpleNamespace(imported_count=2, updated_count=0),
        ],
    )

    results = await run_import_all(container, days=7)

    assert results[0].status == "failed"
    assert results[1].status == "imported"
    assert results[1].imported_count == 2


@pytest.mark.asyncio
async def test_run_import_all_passes_inclusive_date_window() -> None:
    """The import window spans `days` days starting today (inclusive)."""
    cinemas = [SimpleNamespace(id="cin-1", name="Cinema One")]
    container = _make_container(
        cinemas,
        import_side_effect=[SimpleNamespace(imported_count=1, updated_count=0)],
    )

    await run_import_all(container, days=3)

    _, kwargs = container.source_controller.import_screenings.call_args
    assert (kwargs["end_date"] - kwargs["start_date"]).days == 2
