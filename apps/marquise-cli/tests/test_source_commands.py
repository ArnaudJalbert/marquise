"""Tests for source CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from marquise import SourceController
from marquise_cli.source_commands.register_command import run_register_sources
from marquise_cli.source_commands.unregister_command import run_unregister_sources


@dataclass(frozen=True, slots=True)
class _SourceEntry:
    name: str
    display_name: str = "Cinéma Cinéma"


def _make_registry_source_entry(name: str = "cinemacinema") -> _SourceEntry:
    """Build a source registry entry for test setup."""
    return _SourceEntry(name)


@pytest.mark.asyncio
async def test_source_register_new_source(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source register creates a new source after prompting."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_source_controller.create_source = AsyncMock(
        return_value=SimpleNamespace(
            name="cinemacinema",
            display_name="Cinéma Cinéma",
            description="Showtimes for Beaubien, du Parc, and du Musée",
        )
    )
    mock_factory.source = mock_source_controller

    with patch("marquise_cli.source_commands.register_command.questionary") as mock_q:
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=[
                "Cinéma Cinéma",
                "Showtimes for Beaubien, du Parc, and du Musée",
            ]
        )
        await run_register_sources(mock_factory)

    captured = capsys.readouterr()
    assert "cinemacinema" in captured.out
    assert "new" in captured.out
    assert "Created: cinemacinema" in captured.out
    mock_source_controller.create_source.assert_awaited_once_with(
        name="cinemacinema",
        display_name="Cinéma Cinéma",
        description="Showtimes for Beaubien, du Parc, and du Musée",
    )


@pytest.mark.asyncio
async def test_source_register_all_existing(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source register shows all done when nothing new to add."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_SourceEntry("cinemacinema")])
    )
    mock_factory.source = mock_source_controller

    await run_register_sources(mock_factory)

    captured = capsys.readouterr()
    assert "already registered" in captured.out
    assert "All registry sources are already" in captured.out
    mock_source_controller.create_source.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_register_failure(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source register shows error when create_source fails."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_source_controller.create_source = AsyncMock(
        side_effect=ValueError("SourceAlreadyExistsError")
    )
    mock_factory.source = mock_source_controller

    with patch("marquise_cli.source_commands.register_command.questionary") as mock_q:
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=["Cinéma Cinéma", "Showtimes description"]
        )
        await run_register_sources(mock_factory)

    captured = capsys.readouterr()
    assert "Failed: SourceAlreadyExistsError" in captured.err
    assert "  Failed: SourceAlreadyExistsError" in captured.err


@pytest.mark.asyncio
async def test_source_unregister_success(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source unregister removes selected sources after confirmation."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_source_controller.delete_source = AsyncMock(
        return_value=SimpleNamespace(source_name="cinemacinema")
    )
    mock_factory.source = mock_source_controller

    with patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q:
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=True)
        await run_unregister_sources(mock_factory)

    captured = capsys.readouterr()
    assert "in registry" in captured.out
    assert "Removed: cinemacinema" in captured.out
    mock_source_controller.delete_source.assert_awaited_once_with(
        source_name="cinemacinema",
    )


@pytest.mark.asyncio
async def test_source_unregister_no_selection(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source unregister bails when no sources are selected."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_factory.source = mock_source_controller

    with patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q:
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=[])
        await run_unregister_sources(mock_factory)

    captured = capsys.readouterr()
    assert "No sources selected." in captured.out
    mock_source_controller.delete_source.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_unregister_empty_db(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source unregister bails when database has no sources."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_factory.source = mock_source_controller

    await run_unregister_sources(mock_factory)

    captured = capsys.readouterr()
    assert "No sources registered in the database." in captured.out
    mock_source_controller.delete_source.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_unregister_cancelled_at_confirm(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source unregister bails when user declines confirmation."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_factory.source = mock_source_controller

    with patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q:
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=False)
        await run_unregister_sources(mock_factory)

    captured = capsys.readouterr()
    assert "Cancelled." in captured.out
    mock_source_controller.delete_source.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_unregister_partial_failure(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify source unregister shows per-source errors on failure."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_source_controller.delete_source = AsyncMock(
        side_effect=ValueError("Something went wrong")
    )
    mock_factory.source = mock_source_controller

    with patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q:
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=True)
        await run_unregister_sources(mock_factory)

    captured = capsys.readouterr()
    assert "Failed: Something went wrong" in captured.err
