"""Tests for cinema list CLI command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from conftest import make_cinema_data
from marquise import (
    CinemaController,
    ListCinemaSourceAssignmentsQuery,
    ListCinemasUseCase,
)
from marquise_cli.cinema_commands.list_command import run_list_cinemas


def _make_list_mock_cinemas() -> list[ListCinemasUseCase.CinemaData]:
    """Build sample cinema data for list tests."""
    return [
        make_cinema_data(
            cinema_id="cin-001",
            name="Cinema du Parc",
            address="123 Rue du Parc",
            city="Montreal",
            website="https://cinemaduparc.ca",
        ),
        make_cinema_data(
            cinema_id="cin-002",
            name="Quartier Latin",
            address="345 Rue Ontario",
            city="Montreal",
            website=None,
        ),
    ]


@pytest.mark.asyncio
async def test_cinema_list_success(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema list prints cinema names."""
    cinemas = _make_list_mock_cinemas()
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=cinemas, total=len(cinemas))
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    await run_list_cinemas(mock_factory)

    captured = capsys.readouterr()
    assert "Available cinemas" in captured.out
    assert "Cinema" in captured.out
    assert "City" in captured.out
    assert "Cinema du Parc" in captured.out
    assert "Quartier Latin" in captured.out
    assert "Montreal" in captured.out
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_cinema_list_empty(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema list shows 'No cinemas found' when empty."""
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=[], total=0)
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    await run_list_cinemas(mock_factory)

    captured = capsys.readouterr()
    assert "No cinemas found." in captured.out
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_cinema_list_failure(
    mock_factory: MagicMock,
) -> None:
    """Unexpected list failures propagate after factory shutdown."""
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        side_effect=ValueError("Something went wrong")
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with pytest.raises(ValueError, match="Something went wrong"):
        await run_list_cinemas(mock_factory)

    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_cinema_list_verbose(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema list --verbose shows detailed table."""
    cinemas = _make_list_mock_cinemas()
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=cinemas, total=len(cinemas))
    )
    mock_assignment_query = create_autospec(
        ListCinemaSourceAssignmentsQuery, instance=True
    )
    mock_assignment_query.InputData = ListCinemaSourceAssignmentsQuery.InputData
    mock_assignment_query.execute = AsyncMock(
        return_value=ListCinemaSourceAssignmentsQuery.OutputData(
            assignments=[
                SimpleNamespace(
                    cinema_id="cin-001",
                    source_display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.list_cinema_source_assignments_query = mock_assignment_query
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    await run_list_cinemas(mock_factory, verbose=True)

    captured = capsys.readouterr()
    assert "Available cinemas" in captured.out
    assert "Address" in captured.out
    assert "Website" in captured.out
    assert "Source" in captured.out
    assert "Cinéma" in captured.out
    assert "ID" in captured.out
    assert "cin-001" in captured.out
    assert "123" in captured.out
    assert "Parc" in captured.out
    assert "cin-002" in captured.out
    assert "345" in captured.out
    assert "Ontario" in captured.out
    assert "cinem" in captured.out
    mock_assignment_query.execute.assert_awaited_once_with(
        ListCinemaSourceAssignmentsQuery.InputData()
    )
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_cinema_list_renders_markup_like_cinema_name(
    mock_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify cinema names containing Rich markup render literally."""
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(
            cinemas=[make_cinema_data(name="[/bold]")], total=1
        )
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    await run_list_cinemas(mock_factory)

    captured = capsys.readouterr()
    assert "[/bold]" in captured.out


@pytest.mark.parametrize(
    ("website", "expected"),
    [
        ("https://example.com", "https://example.com"),
        ("javascript:alert(1)", "Invalid URL"),
        ("https://example.com/\x1b[2J", "Invalid URL"),
    ],
)
def test_cinema_list_renders_safe_website_text(website: str, expected: str) -> None:
    """Verify only safe HTTP(S) websites are rendered as link destinations."""
    from marquise_cli.cinema_commands.list_command import _website_text

    text = _website_text(website)

    assert text.plain == expected
    assert ("link " in text.style) is (expected == website)


@pytest.mark.asyncio
async def test_cinema_list_with_name_filter(
    mock_factory: MagicMock,
) -> None:
    """Verify cinema list --name passes filter to controller."""
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=[], total=0)
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    await run_list_cinemas(mock_factory, name="Parc")

    mock_cinema_controller.list.assert_called_once_with(name="Parc")
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()
