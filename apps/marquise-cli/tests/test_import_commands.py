"""Tests for bulk import orchestration (`marquise import all`)."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from conftest import make_cinema_data
from marquise import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
    CreateMissingMoviesCommand,
    CreateScreeningsCommand,
    FetchScreeningsFromSourceQuery,
    GetCinemaSourceUseCase,
    ListCinemasUseCase,
    MarquiseFactory,
)
from marquise_cli.helpers import run_spinner
from marquise_cli.import_commands import run_import_all
from marquise_cli.import_commands.cinema_command import (
    _import_screenings,
    run_import_cinema,
)


def _fetched(
    cinema_id: str, cinema_name: str
) -> FetchScreeningsFromSourceQuery.OutputData:
    """Build empty fetched-screenings response for import tests."""
    return FetchScreeningsFromSourceQuery.OutputData(
        cinema_id=cinema_id,
        cinema_name=cinema_name,
        source_name="cineplex",
        movies=(),
        screenings=(),
    )


def _screenings_output(
    imported_count: int, updated_count: int, skipped_count: int = 0
) -> CreateScreeningsCommand.OutputData:
    """Build screenings command response for import tests."""
    return CreateScreeningsCommand.OutputData(
        screenings=(),
        total_count=imported_count + updated_count,
        imported_count=imported_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
    )


def _make_factory(
    cinemas: list[SimpleNamespace],
    fetch_side_effect: BaseException
    | list[FetchScreeningsFromSourceQuery.OutputData | BaseException],
) -> MagicMock:
    """Build fake factory with direct import use cases."""
    factory = create_autospec(MarquiseFactory, instance=True)
    list_cinemas_use_case = create_autospec(ListCinemasUseCase, instance=True)
    list_cinemas_use_case.InputData.side_effect = ListCinemasUseCase.InputData
    list_cinemas_use_case.execute = AsyncMock(
        return_value=SimpleNamespace(cinemas=cinemas)
    )
    factory.list_cinemas_use_case = list_cinemas_use_case
    fetch_use_case = create_autospec(FetchScreeningsFromSourceQuery, instance=True)
    fetch_use_case.execute = AsyncMock(side_effect=fetch_side_effect)
    movies_use_case = create_autospec(CreateMissingMoviesCommand, instance=True)
    movies_use_case.execute = AsyncMock(
        return_value=CreateMissingMoviesCommand.OutputData(movies=())
    )
    screenings_use_case = create_autospec(CreateScreeningsCommand, instance=True)
    screenings_use_case.execute = AsyncMock(
        side_effect=[
            _screenings_output(3, 1),
            _screenings_output(0, 5),
        ]
    )
    factory.fetch_screenings_use_case = fetch_use_case
    factory.create_movies_use_case = movies_use_case
    factory.create_screenings_use_case = screenings_use_case
    return factory


@pytest.mark.asyncio
async def test_import_screenings_executes_direct_use_case_sequence() -> None:
    """Single-cinema import fetches, creates movies, then creates screenings."""
    factory = create_autospec(MarquiseFactory, instance=True)
    fetch_use_case = create_autospec(FetchScreeningsFromSourceQuery, instance=True)
    fetch_use_case.execute = AsyncMock(
        return_value=FetchScreeningsFromSourceQuery.OutputData(
            cinema_id="cin-1",
            cinema_name="Cinema One",
            source_name="cineplex",
            movies=(
                FetchScreeningsFromSourceQuery.FetchedMovieData(title="Movie One"),
            ),
            screenings=(
                FetchScreeningsFromSourceQuery.FetchedScreeningData(
                    movie_title=" Movie  One ",
                    showtime=datetime(2026, 8, 25, tzinfo=UTC),
                ),
            ),
        )
    )
    movies_use_case = create_autospec(CreateMissingMoviesCommand, instance=True)
    movies_use_case.execute = AsyncMock(
        return_value=CreateMissingMoviesCommand.OutputData(
            movies=(
                CreateMissingMoviesCommand.MovieData(title="Movie One", id="movie-1"),
            )
        )
    )
    screenings_use_case = create_autospec(CreateScreeningsCommand, instance=True)
    screenings_use_case.execute = AsyncMock(return_value=_screenings_output(1, 0))
    factory.fetch_screenings_use_case = fetch_use_case
    factory.create_movies_use_case = movies_use_case
    factory.create_screenings_use_case = screenings_use_case

    result = await _import_screenings(
        factory, "cin-1", date(2026, 8, 25), date(2026, 8, 26)
    )

    assert result["source_name"] == "cineplex"
    fetch_use_case.InputData.assert_called_once_with(
        cinema_id="cin-1",
        start_date=date(2026, 8, 25),
        end_date=date(2026, 8, 26),
    )
    movies_use_case.InputData.assert_called_once()
    movies_use_case.MovieInput.assert_called_once()
    assert movies_use_case.MovieInput.call_args.kwargs["title"] == "Movie One"
    screenings_use_case.InputData.assert_called_once()
    screenings_use_case.ScreeningInput.assert_called_once()
    screening_input = screenings_use_case.ScreeningInput.call_args.kwargs
    assert screening_input["movie_id"] == "movie-1"
    assert screening_input["movie_title"] == " Movie  One "


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

    get_source_use_case.InputData.assert_called_once_with(cinema_id="cin-001")
    get_source_use_case.execute.assert_awaited_once()
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
        fetch_side_effect=[
            _fetched("cin-1", "Cinema One"),
            _fetched("cin-2", "Cinema Two"),
        ],
    )

    results = await run_import_all(factory, days=7)

    assert [result.status for result in results] == ["imported", "imported"]
    assert results[0].imported_count == 3
    assert results[1].updated_count == 5
    factory.list_cinemas_use_case.InputData.assert_called_once_with()
    factory.list_cinemas_use_case.execute.assert_awaited_once_with(
        ListCinemasUseCase.InputData()
    )
    factory.fetch_screenings_use_case.execute.assert_awaited()
    assert factory.create_movies_use_case.execute.await_count == 2
    assert factory.create_screenings_use_case.execute.await_count == 2


@pytest.mark.asyncio
async def test_run_import_all_skips_cinema_without_source() -> None:
    """Cinemas without assignment are skipped before later import use cases."""
    factory = _make_factory(
        [SimpleNamespace(id="cin-1", name="Cinema One")],
        fetch_side_effect=CinemaSourceAssignmentNotFoundError("none"),
    )

    results = await run_import_all(factory, days=7)

    assert results[0].status == "skipped"
    factory.create_movies_use_case.execute.assert_not_awaited()
    factory.create_screenings_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_import_all_records_failure_without_aborting() -> None:
    """Fetch failure is recorded while later cinemas continue importing."""
    cinemas = [
        SimpleNamespace(id="cin-1", name="Cinema One"),
        SimpleNamespace(id="cin-2", name="Cinema Two"),
    ]
    factory = _make_factory(
        cinemas,
        fetch_side_effect=[
            CinemaNotFoundError("gone"),
            _fetched("cin-2", "Cinema Two"),
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
        fetch_side_effect=[_fetched("cin-1", "Cinema One")],
    )

    await run_import_all(factory, days=3)

    request = factory.fetch_screenings_use_case.InputData.call_args.kwargs
    assert (request["end_date"] - request["start_date"]).days == 2


@pytest.mark.asyncio
async def test_run_import_all_limits_active_cinema_pipelines() -> None:
    """Bulk import never has more than two active cinema pipelines."""
    cinemas = [
        SimpleNamespace(id=f"cin-{index}", name=f"Cinema {index}") for index in range(4)
    ]
    factory = _make_factory(cinemas, fetch_side_effect=[])
    active = 0
    maximum = 0

    async def fetch(
        request: FetchScreeningsFromSourceQuery.InputData,
    ) -> FetchScreeningsFromSourceQuery.OutputData:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0)
        active -= 1
        return _fetched(request.cinema_id, request.cinema_id)

    factory.fetch_screenings_use_case.execute.side_effect = fetch
    factory.create_screenings_use_case.execute.side_effect = lambda _request: (
        _screenings_output(1, 0)
    )

    results = await run_import_all(factory, days=1)

    assert len(results) == 4
    assert maximum == 2
