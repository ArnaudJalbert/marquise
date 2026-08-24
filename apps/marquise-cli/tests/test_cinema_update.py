"""Tests for cinema update CLI command."""

from __future__ import annotations

from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from conftest import invoke, make_cinema_data
from marquise import (
    CinemaController,
    CinemaNotFoundError,
    ListCinemasUseCase,
    UpdateCinemaUseCase,
)


@pytest.fixture
def mock_cinema_controller_for_update() -> MagicMock:
    """Provide a mocked CinemaController with cinema listing."""
    controller = create_autospec(CinemaController, instance=True)
    controller.list_cinemas = AsyncMock()
    return controller


@pytest.fixture
def mock_update_use_case() -> MagicMock:
    """Provide a mocked UpdateCinemaUseCase."""
    use_case = create_autospec(UpdateCinemaUseCase, instance=True)
    use_case.execute = AsyncMock()
    use_case.InputData = UpdateCinemaUseCase.InputData
    return use_case


def _update_setup(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
    cinema: ListCinemasUseCase.CinemaData | None = None,
) -> dict[str, str | None]:
    """Wire update command collaborators with one cinema."""
    cinema = cinema or make_cinema_data()
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_update
    mock_factory.update_cinema_use_case = mock_update_use_case
    return asdict(cinema)


def test_cinema_update_success(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify cinema update executes use case with selected replacements."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    mock_update_use_case.execute.return_value = UpdateCinemaUseCase.OutputData(
        "cin-001", "Updated Name", "456 New Ave", "Montreal", "https://example.com"
    )
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["name", "address"]
        )
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=["Updated Name", "456 New Ave"]
        )
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "Cinema updated:" in result.stdout
    mock_update_use_case.execute.assert_awaited_once_with(
        UpdateCinemaUseCase.InputData(
            "cin-001", "Updated Name", "456 New Ave", "Montreal", "https://example.com"
        )
    )
    mock_factory.__aenter__.assert_awaited_once()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_update_clear_optional_field(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify cinema update supports clearing optional fields."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    mock_update_use_case.execute.return_value = UpdateCinemaUseCase.OutputData(
        "cin-001", "Test Cinema"
    )
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["address"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="")
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    mock_update_use_case.execute.assert_awaited_once_with(
        UpdateCinemaUseCase.InputData(
            "cin-001", "Test Cinema", None, "Montreal", "https://example.com"
        )
    )


@pytest.mark.parametrize("selection", [None, "__exit__"])
def test_cinema_update_cancelled_at_select(
    selection: str | None,
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify cinema selection cancellation performs no update."""
    _update_setup(mock_factory, mock_cinema_controller_for_update, mock_update_use_case)
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=selection)
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_update_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("fields", [None, []])
def test_cinema_update_cancelled_at_fields(
    fields: list[str] | None,
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify empty field selection performs no update."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=fields)
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "No fields selected. Cancelled." in result.stdout
    mock_update_use_case.execute.assert_not_awaited()


def test_cinema_update_cancelled_at_value(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify field-value cancellation performs no update."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["name"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value=None)
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_update_use_case.execute.assert_not_awaited()


def test_cinema_update_no_cinemas(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify empty cinema list is reported clearly."""
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[], total=0)
    )
    mock_factory.cinema = mock_cinema_controller_for_update
    mock_factory.update_cinema_use_case = mock_update_use_case
    with patch(
        "marquise_cli.cinema_commands.update_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "No cinemas available to update." in result.stdout
    mock_update_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [ValueError("name must not be empty"), CinemaNotFoundError("cinema was not found")],
)
def test_cinema_update_failure(
    error: Exception,
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify documented update errors reach stderr with exit code one."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    mock_update_use_case.execute.side_effect = error
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["name"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="New Name")
        result = invoke(["cinema", "update"])
    assert result.exit_code == 1
    assert f"Failed to update cinema: {error}" in result.stderr


def test_cinema_update_unexpected_failure_propagates(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify unexpected update failures propagate after factory cleanup."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    mock_update_use_case.execute.side_effect = RuntimeError("database unavailable")
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
        pytest.raises(RuntimeError, match="database unavailable"),
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["name"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="New Name")
        invoke(["cinema", "update"])
    mock_factory.__aexit__.assert_awaited_once()
