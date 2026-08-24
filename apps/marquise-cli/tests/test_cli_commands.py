"""Tests for source CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

from conftest import invoke
from marquise import SourceController


@dataclass(frozen=True, slots=True)
class _SourceEntry:
    name: str
    display_name: str = "Cinéma Cinéma"


def _make_registry_source_entry(name: str = "cinemacinema") -> _SourceEntry:
    """Build a source registry entry for test setup."""
    return _SourceEntry(name)


def test_source_register_new_source(
    mock_factory: MagicMock,
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
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.register_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.register_command.questionary") as mock_q,
    ):
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=[
                "Cinéma Cinéma",
                "Showtimes for Beaubien, du Parc, and du Musée",
            ]
        )

        result = invoke(["source", "register"])

    assert result.exit_code == 0
    assert "cinemacinema" in result.stdout
    assert "new" in result.stdout
    assert "Created: cinemacinema" in result.stdout
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()
    mock_source_controller.create_source.assert_awaited_once_with(
        name="cinemacinema",
        display_name="Cinéma Cinéma",
        description="Showtimes for Beaubien, du Parc, and du Musée",
    )


def test_source_register_all_existing(
    mock_factory: MagicMock,
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
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.source_commands.register_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["source", "register"])

    assert result.exit_code == 0
    assert "already registered" in result.stdout
    assert "All registry sources are already" in result.stdout
    mock_source_controller.create_source.assert_not_awaited()
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


def test_source_register_failure(
    mock_factory: MagicMock,
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
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.register_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.register_command.questionary") as mock_q,
    ):
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=["Cinéma Cinéma", "Showtimes description"]
        )

        result = invoke(["source", "register"])

    assert result.exit_code == 0
    assert "Failed: SourceAlreadyExistsError" in result.stderr
    assert "  Failed: SourceAlreadyExistsError" in result.stderr


def test_source_unregister_success(
    mock_factory: MagicMock,
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
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.unregister_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q,
    ):
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=True)

        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "in registry" in result.stdout
    assert "Removed: cinemacinema" in result.stdout
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()
    mock_source_controller.delete_source.assert_awaited_once_with(
        source_name="cinemacinema",
    )


def test_source_unregister_no_selection(
    mock_factory: MagicMock,
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
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.unregister_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q,
    ):
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=[])

        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "No sources selected." in result.stdout
    mock_source_controller.delete_source.assert_not_awaited()


def test_source_unregister_empty_db(
    mock_factory: MagicMock,
) -> None:
    """Verify source unregister bails when database has no sources."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.source_commands.unregister_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "No sources registered in the database." in result.stdout
    mock_source_controller.delete_source.assert_not_awaited()


def test_source_unregister_cancelled_at_confirm(
    mock_factory: MagicMock,
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
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.unregister_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q,
    ):
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=False)

        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_source_controller.delete_source.assert_not_awaited()


def test_source_unregister_partial_failure(
    mock_factory: MagicMock,
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
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.unregister_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.unregister_command.questionary") as mock_q,
    ):
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=True)

        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "Failed: Something went wrong" in result.stderr
