"""Tests for cinema delete CLI command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from conftest import invoke, make_cinema_data
from marquise import (
    CinemaController,
    CinemaNotFoundError,
    DeleteCinemaUseCase,
    ListCinemasUseCase,
)


@pytest.fixture
def mock_cinema_controller_for_delete() -> MagicMock:
    """Provide a mocked CinemaController with list methods."""
    controller = create_autospec(CinemaController, instance=True)
    controller.list_cinemas = AsyncMock()
    return controller


@pytest.fixture
def mock_delete_use_case() -> MagicMock:
    """Provide a mocked DeleteCinemaUseCase."""
    use_case = create_autospec(DeleteCinemaUseCase, instance=True)
    use_case.execute = AsyncMock()
    use_case.InputData = DeleteCinemaUseCase.InputData
    return use_case


def test_cinema_delete_success(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete uses direct use-case execution after confirmation."""
    cinema = make_cinema_data()
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Test Cinema")
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 0
    assert 'Cinema "Test Cinema" (ID: cin-001) deleted.' in result.stdout
    mock_delete_use_case.execute.assert_awaited_once_with(
        DeleteCinemaUseCase.InputData(cinema_id="cin-001")
    )
    mock_factory.__aenter__.assert_awaited_once()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_delete_name_mismatch(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete aborts when confirmation name does not match."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[make_cinema_data()], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Wrong Name")
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 1
    assert 'Name mismatch: expected "Test Cinema", got "Wrong Name"' in result.stderr
    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_delete_no_cinemas(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete handles an empty cinema list."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[], total=0)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with patch(
        "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 0
    assert "No cinemas available to delete." in result.stdout
    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_delete_list_failure(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Unexpected cinema-list errors propagate after factory cleanup."""
    mock_cinema_controller_for_delete.list_cinemas.side_effect = ValueError(
        "Database unavailable"
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        pytest.raises(ValueError, match="Database unavailable"),
    ):
        invoke(["cinema", "delete"])

    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("selection", [None, "__exit__"])
def test_cinema_delete_cancelled_at_select(
    selection: str | None,
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete handles selection cancellation."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[make_cinema_data()], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=selection)
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_delete_cancelled_at_confirmation(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete handles confirmation cancellation."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[make_cinema_data()], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value=None)
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


@pytest.mark.parametrize(
    "error",
    [
        ValueError("cinema_id must not be empty"),
        CinemaNotFoundError("cinema was not found"),
    ],
)
def test_cinema_delete_failure(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
    error: Exception,
) -> None:
    """Every delete use-case error is shown and exits unsuccessfully."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[make_cinema_data()], total=1)
    )
    mock_delete_use_case.execute.side_effect = error
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Test Cinema")
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 1
    assert f"Failed to delete cinema: {error}" in result.stderr
    mock_factory.__aexit__.assert_awaited_once()
