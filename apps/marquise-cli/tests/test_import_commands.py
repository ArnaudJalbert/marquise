"""Tests for bulk import orchestration (`marquise import all`)."""

from __future__ import annotations

import asyncio
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
    ListCinemasUseCase,
    MarquiseFactory,
)
from marquise_cli.helpers import run_spinner
from marquise_cli.import_commands import import_all, run_import_all
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
    factory.list_cinemas_use_case = create_autospec(ListCinemasUseCase, instance=True)
    factory.list_cinemas_use_case.execute = AsyncMock(
        return_value=SimpleNamespace(cinemas=cinemas)
    )
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
        "rescheduled_count": 0,
        "skipped_count": 0,
        "skipped_movies": (),
        "unmatched_movies": (),
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
    get_source_use_case.InputData = MagicMock(wraps=GetCinemaSourceUseCase.InputData)
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
    get_source_use_case.InputData.assert_called_once_with(cinema_id="cin-001")
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


@pytest.mark.asyncio
async def test_run_import_all_limits_active_cinema_pipelines() -> None:
    """Bulk import never has more than two active cinema pipelines."""
    cinemas = [
        SimpleNamespace(id=f"cin-{index}", name=f"Cinema {index}") for index in range(4)
    ]
    factory = _make_factory(cinemas, import_side_effect=[])
    active = 0
    maximum = 0

    async def import_cinema(
        request: ImportScreeningsCommand.InputData,
    ) -> ImportScreeningsCommand.OutputData:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0)
        active -= 1
        return ImportScreeningsCommand.OutputData(
            request.cinema_id, request.cinema_id, "cineplex", (), 1, 1, 0, 0
        )

    factory.import_screenings_use_case.execute.side_effect = import_cinema

    results = await run_import_all(factory, days=1)

    assert len(results) == 4
    assert maximum == 2


def test_import_all_stays_green_when_only_movies_are_skipped() -> None:
    """Movies skipped inside an imported cinema do not fail the scheduled job."""
    factory = _make_factory(
        [SimpleNamespace(id="cin-1", name="Cinema One")],
        import_side_effect=[
            ImportScreeningsCommand.OutputData(
                "cin-1", "Cinema One", "cineplex", (), 2, 2, 0, 0
            )
        ],
    )
    with patch(
        "marquise_cli.import_commands.all_command.MarquiseFactory",
        return_value=factory,
    ):
        import_all(days=1)


def test_import_all_turns_red_when_a_cinema_fails() -> None:
    """A cinema that fails outright makes the scheduled job exit with an error."""
    factory = _make_factory(
        [SimpleNamespace(id="cin-1", name="Cinema One")],
        import_side_effect=RuntimeError("TMDB unavailable"),
    )
    with (
        patch(
            "marquise_cli.import_commands.all_command.MarquiseFactory",
            return_value=factory,
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        import_all(days=1)
    assert exit_info.value.code == 1


def test_import_all_reports_skipped_and_unmatched_movies(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each cinema and the whole run list skipped and unmatched movies by reason."""
    unresolved = ImportScreeningsCommand.UnresolvedMovieData
    factory = _make_factory(
        [
            SimpleNamespace(id="cin-1", name="Cinema One"),
            SimpleNamespace(id="cin-2", name="Cinema Two"),
        ],
        import_side_effect=[
            ImportScreeningsCommand.OutputData(
                "cin-1",
                "Cinema One",
                "cineplex",
                (),
                3,
                3,
                0,
                0,
                skipped_movies=(
                    unresolved("Twin Peaks", "MetadataDetailMappingError"),
                ),
                unmatched_movies=(unresolved("Mystery Night", "no_match"),),
            ),
            ImportScreeningsCommand.OutputData(
                "cin-2",
                "Cinema Two",
                "cineplex",
                (),
                2,
                2,
                0,
                0,
                skipped_movies=(unresolved("SCENE TAM", "MetadataDetailMappingError"),),
            ),
        ],
    )
    with patch(
        "marquise_cli.import_commands.all_command.MarquiseFactory",
        return_value=factory,
    ):
        import_all(days=1)

    output = capsys.readouterr().out
    assert (
        "\nMovies for Cinema One: MetadataDetailMappingError 1, no_match 1\n"
        "  Skipped:\n"
        "    Cinema One | Twin Peaks | MetadataDetailMappingError\n"
        "  Unmatched:\n"
        "    Cinema One | Mystery Night | no_match\n"
    ) in output
    assert (
        "\nMovies for Cinema Two: MetadataDetailMappingError 1\n"
        "  Skipped:\n"
        "    Cinema Two | SCENE TAM | MetadataDetailMappingError\n"
    ) in output
    assert (
        "\nMovies for the run: MetadataDetailMappingError 2, no_match 1\n"
        "  Skipped:\n"
        "    Cinema One | Twin Peaks | MetadataDetailMappingError\n"
        "    Cinema Two | SCENE TAM | MetadataDetailMappingError\n"
        "  Unmatched:\n"
        "    Cinema One | Mystery Night | no_match\n"
    ) in output


def test_import_all_reports_a_run_with_every_movie_matched(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A run with nothing skipped or unmatched says so once."""
    factory = _make_factory(
        [SimpleNamespace(id="cin-1", name="Cinema One")],
        import_side_effect=[
            ImportScreeningsCommand.OutputData(
                "cin-1", "Cinema One", "cineplex", (), 1, 1, 0, 0
            )
        ],
    )
    with patch(
        "marquise_cli.import_commands.all_command.MarquiseFactory",
        return_value=factory,
    ):
        import_all(days=1)

    output = capsys.readouterr().out
    assert "Movies for the run: none skipped or unmatched\n" in output
    assert "Movies for Cinema One" not in output
