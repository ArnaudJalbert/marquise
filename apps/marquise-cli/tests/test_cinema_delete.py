"""Tests for cinema delete CLI command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from conftest import make_cinema_data, mock_use_case, patch_questionary
from marquise import CinemaNotFoundError, DeleteCinemaUseCase, ListCinemasQuery
from marquise_cli.cinema_commands.delete_command import run_delete


@pytest.fixture
def mock_delete_use_case() -> MagicMock:
    """Provide a mocked DeleteCinemaUseCase."""
    return mock_use_case(DeleteCinemaUseCase)


@pytest.mark.asyncio
async def test_cinema_delete_success(
    mock_factory: MagicMock,
    mock_list_cinemas_query: MagicMock,
    mock_delete_use_case: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema delete uses direct use-case execution after confirmation."""
    cinema = make_cinema_data()
    mock_list_cinemas_query.execute.return_value = ListCinemasQuery.OutputData(
        cinemas=[cinema], total=1
    )
    mock_factory.cinemas.list_cinemas_query = mock_list_cinemas_query
    mock_factory.cinemas.delete_cinema_use_case = mock_delete_use_case

    with patch_questionary("marquise_cli.cinema_commands.delete_command") as mock_q:
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Test Cinema")
        await run_delete(mock_factory)

    captured = capsys.readouterr()
    assert 'Cinema "Test Cinema" (ID: cin-001) deleted.' in captured.out
    mock_list_cinemas_query.execute.assert_awaited_once_with(
        ListCinemasQuery.InputData(page=1, size=100)
    )
    mock_delete_use_case.execute.assert_awaited_once_with(
        DeleteCinemaUseCase.InputData(cinema_id="cin-001")
    )


@pytest.mark.asyncio
async def test_cinema_delete_name_mismatch(
    mock_factory: MagicMock,
    mock_list_cinemas_query: MagicMock,
    mock_delete_use_case: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema delete aborts when confirmation name does not match."""
    mock_list_cinemas_query.execute.return_value = ListCinemasQuery.OutputData(
        cinemas=[make_cinema_data()], total=1
    )
    mock_factory.cinemas.list_cinemas_query = mock_list_cinemas_query
    mock_factory.cinemas.delete_cinema_use_case = mock_delete_use_case

    with (
        patch_questionary("marquise_cli.cinema_commands.delete_command") as mock_q,
        pytest.raises(SystemExit),
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Wrong Name")
        await run_delete(mock_factory)

    captured = capsys.readouterr()
    assert 'Name mismatch: expected "Test Cinema", got "Wrong Name"' in captured.err
    mock_delete_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cinema_delete_no_cinemas(
    mock_factory: MagicMock,
    mock_list_cinemas_query: MagicMock,
    mock_delete_use_case: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema delete handles an empty cinema list."""
    mock_list_cinemas_query.execute.return_value = ListCinemasQuery.OutputData(
        cinemas=[], total=0
    )
    mock_factory.cinemas.list_cinemas_query = mock_list_cinemas_query
    mock_factory.cinemas.delete_cinema_use_case = mock_delete_use_case

    await run_delete(mock_factory)

    captured = capsys.readouterr()
    assert "No cinemas available." in captured.out
    mock_delete_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cinema_delete_list_failure(
    mock_factory: MagicMock,
    mock_list_cinemas_query: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Unexpected cinema-list errors propagate."""
    mock_list_cinemas_query.execute.side_effect = ValueError("Database unavailable")
    mock_factory.cinemas.list_cinemas_query = mock_list_cinemas_query
    mock_factory.cinemas.delete_cinema_use_case = mock_delete_use_case

    with pytest.raises(ValueError, match="Database unavailable"):
        await run_delete(mock_factory)

    mock_delete_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("selection", [None, "__exit__"])
@pytest.mark.asyncio
async def test_cinema_delete_cancelled_at_select(
    selection: str | None,
    mock_factory: MagicMock,
    mock_list_cinemas_query: MagicMock,
    mock_delete_use_case: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema delete handles selection cancellation."""
    mock_list_cinemas_query.execute.return_value = ListCinemasQuery.OutputData(
        cinemas=[make_cinema_data()], total=1
    )
    mock_factory.cinemas.list_cinemas_query = mock_list_cinemas_query
    mock_factory.cinemas.delete_cinema_use_case = mock_delete_use_case

    with patch_questionary("marquise_cli.cinema_commands.delete_command") as mock_q:
        mock_q.select.return_value.ask_async = AsyncMock(return_value=selection)
        await run_delete(mock_factory)

    captured = capsys.readouterr()
    assert "Cancelled." in captured.out
    mock_delete_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cinema_delete_cancelled_at_confirmation(
    mock_factory: MagicMock,
    mock_list_cinemas_query: MagicMock,
    mock_delete_use_case: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema delete handles confirmation cancellation."""
    mock_list_cinemas_query.execute.return_value = ListCinemasQuery.OutputData(
        cinemas=[make_cinema_data()], total=1
    )
    mock_factory.cinemas.list_cinemas_query = mock_list_cinemas_query
    mock_factory.cinemas.delete_cinema_use_case = mock_delete_use_case

    with patch_questionary("marquise_cli.cinema_commands.delete_command") as mock_q:
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value=None)
        await run_delete(mock_factory)

    captured = capsys.readouterr()
    assert "Cancelled." in captured.out
    mock_delete_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [
        ValueError("cinema_id must not be empty"),
        CinemaNotFoundError("cinema was not found"),
    ],
)
@pytest.mark.asyncio
async def test_cinema_delete_failure(
    mock_factory: MagicMock,
    mock_list_cinemas_query: MagicMock,
    mock_delete_use_case: MagicMock,
    error: Exception,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every delete use-case error is shown and exits unsuccessfully."""
    mock_list_cinemas_query.execute.return_value = ListCinemasQuery.OutputData(
        cinemas=[make_cinema_data()], total=1
    )
    mock_delete_use_case.execute.side_effect = error
    mock_factory.cinemas.list_cinemas_query = mock_list_cinemas_query
    mock_factory.cinemas.delete_cinema_use_case = mock_delete_use_case

    with (
        patch_questionary("marquise_cli.cinema_commands.delete_command") as mock_q,
        pytest.raises(SystemExit),
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Test Cinema")
        await run_delete(mock_factory)

    captured = capsys.readouterr()
    assert f"Failed to delete cinema: {error}" in captured.err
