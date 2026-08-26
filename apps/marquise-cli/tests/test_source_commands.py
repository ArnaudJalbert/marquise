"""Tests for source CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from conftest import make_cinema_data
from marquise import (
    AssignSourceUseCase,
    CreateSourceUseCase,
    DeleteSourceUseCase,
    ListRegistrySourcesUseCase,
    ListSourcesUseCase,
    UnassignSourceUseCase,
)
from marquise_cli.helpers import select_source
from marquise_cli.source_commands.assign_command import run_assign
from marquise_cli.source_commands.list_registered_command import (
    run_list_registered_sources,
)
from marquise_cli.source_commands.register_command import run_register_sources
from marquise_cli.source_commands.unassign_command import run_unassign
from marquise_cli.source_commands.unregister_command import run_unregister_sources


@dataclass(frozen=True, slots=True)
class _SourceEntry:
    name: str
    display_name: str = "Cinéma Cinéma"
    description: str | None = None


def _registry_use_case(sources: list[_SourceEntry]) -> MagicMock:
    """Build configured registry-source use-case mock."""
    use_case = create_autospec(ListRegistrySourcesUseCase, instance=True)
    use_case.execute = AsyncMock(return_value=SimpleNamespace(sources=sources))
    return use_case


def _list_use_case(sources: list[_SourceEntry]) -> MagicMock:
    """Build configured registered-source use-case mock."""
    use_case = create_autospec(ListSourcesUseCase, instance=True)
    use_case.execute = AsyncMock(return_value=SimpleNamespace(sources=sources))
    return use_case


@pytest.mark.asyncio
async def test_select_source_executes_list_use_case_and_handles_cancellation(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source selection lists sources directly and preserves cancellation."""
    list_sources_use_case = _list_use_case([_SourceEntry("cinemacinema")])
    mock_factory.list_sources_use_case = list_sources_use_case

    with patch("marquise_cli.helpers.questionary.select") as select:
        select.return_value.ask_async = AsyncMock(return_value="__exit__")
        selected = await select_source(mock_factory, "Select a source:")

    assert selected is None
    assert "Cancelled." in capsys.readouterr().out
    list_sources_use_case.InputData.assert_called_once_with()
    list_sources_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_source_list_executes_list_use_case(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source listing executes direct use case and cleans up factory."""
    list_sources_use_case = _list_use_case([_SourceEntry("cinemacinema")])
    mock_factory.list_sources_use_case = list_sources_use_case

    await run_list_registered_sources(mock_factory)

    assert "cinemacinema" in capsys.readouterr().out
    list_sources_use_case.InputData.assert_called_once_with()
    list_sources_use_case.execute.assert_awaited_once()
    mock_factory.initialize.assert_awaited_once()
    mock_factory.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_source_assign_executes_assign_use_case(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source assignment sends selected values and cleans up factory."""
    assign_source_use_case = create_autospec(AssignSourceUseCase, instance=True)
    assign_source_use_case.execute = AsyncMock(
        return_value=AssignSourceUseCase.OutputData(
            cinema_id="cin-001",
            source_name="cinemacinema",
        )
    )
    mock_factory.assign_source_use_case = assign_source_use_case

    with (
        patch(
            "marquise_cli.source_commands.assign_command.select_cinema",
            new=AsyncMock(return_value=make_cinema_data()),
        ),
        patch(
            "marquise_cli.source_commands.assign_command.select_source",
            new=AsyncMock(return_value="cinemacinema"),
        ),
    ):
        await run_assign(mock_factory)

    assert "Source assigned:" in capsys.readouterr().out
    assign_source_use_case.InputData.assert_called_once_with(
        cinema_id="cin-001", source_name="cinemacinema"
    )
    assign_source_use_case.execute.assert_awaited_once()
    mock_factory.initialize.assert_awaited_once()
    mock_factory.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_source_unassign_executes_unassign_use_case(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source unassignment sends cinema ID and cleans up factory."""
    unassign_source_use_case = create_autospec(UnassignSourceUseCase, instance=True)
    unassign_source_use_case.execute = AsyncMock(
        return_value=UnassignSourceUseCase.OutputData(cinema_id="cin-001")
    )
    mock_factory.unassign_source_use_case = unassign_source_use_case

    with patch(
        "marquise_cli.source_commands.unassign_command.select_cinema",
        new=AsyncMock(return_value=make_cinema_data()),
    ):
        await run_unassign(mock_factory)

    assert "Source unassigned from cinema cin-001." in capsys.readouterr().out
    unassign_source_use_case.InputData.assert_called_once_with(cinema_id="cin-001")
    unassign_source_use_case.execute.assert_awaited_once()
    mock_factory.initialize.assert_awaited_once()
    mock_factory.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_source_register_new_source(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source register executes create use case after prompting."""
    create_use_case = create_autospec(CreateSourceUseCase, instance=True)
    create_use_case.execute = AsyncMock(
        return_value=SimpleNamespace(name="cinemacinema")
    )
    mock_factory.list_registry_sources_use_case = _registry_use_case(
        [_SourceEntry("cinemacinema")]
    )
    mock_factory.list_sources_use_case = _list_use_case([])
    mock_factory.create_source_use_case = create_use_case

    with patch("marquise_cli.source_commands.register_command.questionary") as mock_q:
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=["Cinéma Cinéma", "Showtimes for Beaubien"]
        )
        await run_register_sources(mock_factory)

    assert "Created: cinemacinema" in capsys.readouterr().out
    create_use_case.InputData.assert_called_once_with(
        name="cinemacinema",
        display_name="Cinéma Cinéma",
        description="Showtimes for Beaubien",
    )
    create_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_source_register_all_existing(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source register does not create existing sources."""
    create_use_case = create_autospec(CreateSourceUseCase, instance=True)
    mock_factory.list_registry_sources_use_case = _registry_use_case(
        [_SourceEntry("cinemacinema")]
    )
    mock_factory.list_sources_use_case = _list_use_case([_SourceEntry("cinemacinema")])
    mock_factory.create_source_use_case = create_use_case

    await run_register_sources(mock_factory)

    assert "All registry sources are already" in capsys.readouterr().out
    create_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_register_failure(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source register reports create use-case errors."""
    create_use_case = create_autospec(CreateSourceUseCase, instance=True)
    create_use_case.execute = AsyncMock(side_effect=ValueError("already exists"))
    mock_factory.list_registry_sources_use_case = _registry_use_case(
        [_SourceEntry("cinemacinema")]
    )
    mock_factory.list_sources_use_case = _list_use_case([])
    mock_factory.create_source_use_case = create_use_case

    with patch("marquise_cli.source_commands.register_command.questionary") as mock_q:
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=["Cinéma Cinéma", "Showtimes description"]
        )
        await run_register_sources(mock_factory)

    assert "Failed: already exists" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_source_unregister_success(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source unregister executes delete use case after confirmation."""
    delete_use_case = create_autospec(DeleteSourceUseCase, instance=True)
    delete_use_case.execute = AsyncMock()
    mock_factory.list_registry_sources_use_case = _registry_use_case(
        [_SourceEntry("cinemacinema")]
    )
    mock_factory.list_sources_use_case = _list_use_case([_SourceEntry("cinemacinema")])
    mock_factory.delete_source_use_case = delete_use_case

    with patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q:
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=True)
        await run_unregister_sources(mock_factory)

    assert "Removed: cinemacinema" in capsys.readouterr().out
    delete_use_case.InputData.assert_called_once_with(source_name="cinemacinema")
    delete_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_source_unregister_no_selection(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source unregister does not delete without selection."""
    delete_use_case = create_autospec(DeleteSourceUseCase, instance=True)
    mock_factory.list_registry_sources_use_case = _registry_use_case(
        [_SourceEntry("cinemacinema")]
    )
    mock_factory.list_sources_use_case = _list_use_case([_SourceEntry("cinemacinema")])
    mock_factory.delete_source_use_case = delete_use_case

    with patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q:
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=[])
        await run_unregister_sources(mock_factory)

    assert "No sources selected." in capsys.readouterr().out
    delete_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_unregister_empty_db(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source unregister exits when database has no sources."""
    delete_use_case = create_autospec(DeleteSourceUseCase, instance=True)
    mock_factory.list_registry_sources_use_case = _registry_use_case([])
    mock_factory.list_sources_use_case = _list_use_case([])
    mock_factory.delete_source_use_case = delete_use_case

    await run_unregister_sources(mock_factory)

    assert "No sources registered in the database." in capsys.readouterr().out
    delete_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_unregister_cancelled_at_confirm(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source unregister does not delete when confirmation is declined."""
    delete_use_case = create_autospec(DeleteSourceUseCase, instance=True)
    mock_factory.list_registry_sources_use_case = _registry_use_case(
        [_SourceEntry("cinemacinema")]
    )
    mock_factory.list_sources_use_case = _list_use_case([_SourceEntry("cinemacinema")])
    mock_factory.delete_source_use_case = delete_use_case

    with patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q:
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=False)
        await run_unregister_sources(mock_factory)

    assert "Cancelled." in capsys.readouterr().out
    delete_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_unregister_partial_failure(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source unregister reports each delete use-case failure."""
    delete_use_case = create_autospec(DeleteSourceUseCase, instance=True)
    delete_use_case.execute = AsyncMock(side_effect=ValueError("Something went wrong"))
    mock_factory.list_registry_sources_use_case = _registry_use_case(
        [_SourceEntry("cinemacinema")]
    )
    mock_factory.list_sources_use_case = _list_use_case([_SourceEntry("cinemacinema")])
    mock_factory.delete_source_use_case = delete_use_case

    with patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q:
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=True)
        await run_unregister_sources(mock_factory)

    assert "Failed: Something went wrong" in capsys.readouterr().err
