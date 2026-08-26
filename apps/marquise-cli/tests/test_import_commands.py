"""Tests for bulk import orchestration (`marquise import all`)."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from conftest import make_cinema_data
from marquise import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
    GetCinemaSourceUseCase,
    ImportScreeningsCommand,
    MarquiseFactory,
)
from marquise_cli.helpers import run_spinner
from marquise_cli.import_commands import run_import_all
from marquise_cli.import_commands.cinema_command import (
    _import_screenings,
    run_import_cinema,
)


def _make_factory(
    cinemas: list[SimpleNamespace],
    import_side_effect: BaseException
    | list[ImportScreeningsCommand.OutputData | BaseException],
) -> MagicMock:
    """Build fake factory with the import use case."""
    factory = create_autospec(MarquiseFactory, instance=True)
    factory.cinema.list = AsyncMock(return_value=SimpleNamespace(cinemas=cinemas))
    import_use_case = create_autospec(ImportScreeningsCommand, instance=True)
    import_use_case.execute = AsyncMock(side_effect=import_side_effect)
    factory.import_screenings_use_case = import_use_case
    return factory


@pytest.mark.asyncio
async def test_import_screenings_delegates_to_import_use_case() -> None:
    """Single-cinema import passes its input to the application use case."""
    factory = create_autospec(MarquiseFactory, instance=True)
    import_use_case = create_autospec(ImportScreeningsCommand, instance=True)
    expected = ImportScreeningsCommand.OutputData(
        "cin-1", "Cinema One", "cineplex", (), 0, 0, 0, 0
    )
    import_use_case.execute = AsyncMock(return_value=expected)
    factory.import_screenings_use_case = import_use_case

    result = await _import_screenings(
        factory, "cin-1", date(2026, 8, 25), date(2026, 8, 26)
    )

    assert result == {
        "cinema_id": "cin-1",
        "cinema_name": "Cinema One",
        "source_name": "cineplex",
        "screenings": (),
        "total_count": 0,
        "imported_count": 0,
        "updated_count": 0,
        "skipped_count": 0,
    }
    import_use_case.execute.assert_awaited_once_with(
        ImportScreeningsCommand.InputData(
            cinema_id="cin-1",
            start_date=date(2026, 8, 25),
            end_date=date(2026, 8, 26),
        )
    )


@pytest.mark.asyncio
async def test_run_import_cinema_looks_up_source_and_spins_full_import(
    mock_factory: MagicMock,
) -> None:
    """Verify source lookup and full import retain direct DTOs, spinner, and cleanup."""
    get_source_use_case = create_autospec(GetCinemaSourceUseCase, instance=True)
    get_source_use_case.execute = AsyncMock(
        return_value=GetCinemaSourceUseCase.OutputData(
            cinema_id="cin-001",
            source_name="cinemacinema",
            source_display_name="Cinéma Cinéma",
        )
    )
    mock_factory.get_cinema_source_use_case = get_source_use_case
    import_result = {
        "cinema_name": "Test Cinema",
        "source_name": "cinemacinema",
        "screenings": (),
        "total_count": 0,
        "imported_count": 0,
        "updated_count": 0,
        "skipped_count": 0,
    }

    with (
        patch(
            "marquise_cli.import_commands.cinema_command.select_cinema",
            new=AsyncMock(return_value=make_cinema_data()),
        ),
        patch(
            "marquise_cli.import_commands.cinema_command._select_date_range",
            new=AsyncMock(return_value=(date(2026, 8, 25), date(2026, 8, 26))),
        ),
        patch(
            "marquise_cli.import_commands.cinema_command._import_screenings",
            new=AsyncMock(return_value=import_result),
        ) as import_screenings,
        patch(
            "marquise_cli.import_commands.cinema_command.run_spinner",
            wraps=run_spinner,
        ) as spinner,
    ):
        await run_import_cinema(mock_factory)

    get_source_use_case.execute.assert_awaited_once_with(
        GetCinemaSourceUseCase.InputData(cinema_id="cin-001")
    )
    import_screenings.assert_awaited_once_with(
        mock_factory,
        "cin-001",
        date(2026, 8, 25),
        date(2026, 8, 26),
    )
    assert spinner.await_args_list[1].kwargs == {
        "description": "Importing screenings..."
    }
    mock_factory.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_import_all_imports_each_cinema() -> None:
    """Every cinema with a source executes direct import use cases."""
    cinemas = [
        SimpleNamespace(id="cin-1", name="Cinema One"),
        SimpleNamespace(id="cin-2", name="Cinema Two"),
    ]
    factory = _make_factory(
        cinemas,
        import_side_effect=[
            ImportScreeningsCommand.OutputData(
                "cin-1", "Cinema One", "cineplex", (), 4, 3, 1, 0
            ),
            ImportScreeningsCommand.OutputData(
                "cin-2", "Cinema Two", "cineplex", (), 5, 0, 5, 0
            ),
        ],
    )

    results = await run_import_all(factory, days=7)

    assert [result.status for result in results] == ["imported", "imported"]
    assert results[0].imported_count == 3
    assert results[1].updated_count == 5
    assert factory.import_screenings_use_case.execute.await_count == 2


@pytest.mark.asyncio
async def test_run_import_all_skips_cinema_without_source() -> None:
    """Cinemas without assignment are skipped before later import use cases."""
    factory = _make_factory(
        [SimpleNamespace(id="cin-1", name="Cinema One")],
        import_side_effect=CinemaSourceAssignmentNotFoundError("none"),
    )

    results = await run_import_all(factory, days=7)

    assert results[0].status == "skipped"
    factory.import_screenings_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_import_all_records_failure_without_aborting() -> None:
    """Fetch failure is recorded while later cinemas continue importing."""
    cinemas = [
        SimpleNamespace(id="cin-1", name="Cinema One"),
        SimpleNamespace(id="cin-2", name="Cinema Two"),
    ]
    factory = _make_factory(
        cinemas,
        import_side_effect=[
            CinemaNotFoundError("gone"),
            ImportScreeningsCommand.OutputData(
                "cin-2", "Cinema Two", "cineplex", (), 3, 3, 0, 0
            ),
        ],
    )

    results = await run_import_all(factory, days=7)

    assert results[0].status == "failed"
    assert results[1].status == "imported"
    assert results[1].imported_count == 3


@pytest.mark.asyncio
async def test_run_import_all_passes_inclusive_date_window() -> None:
    """Fetch query receives a window spanning requested inclusive day count."""
    factory = _make_factory(
        [SimpleNamespace(id="cin-1", name="Cinema One")],
        import_side_effect=[
            ImportScreeningsCommand.OutputData(
                "cin-1", "Cinema One", "cineplex", (), 0, 0, 0, 0
            )
        ],
    )

    await run_import_all(factory, days=3)

    request = factory.import_screenings_use_case.execute.call_args.args[0]
    assert isinstance(request, ImportScreeningsCommand.InputData)
    assert (request.end_date - request.start_date).days == 2
