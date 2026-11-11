"""Unit tests for the reader-backed screening detail query."""

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.queries.get_screening import GetScreeningQuery
from marquise.application.readers import ScreeningReader


@pytest.mark.asyncio
async def test_returns_screening_projection() -> None:
    """The query returns only display data through its own output DTO."""
    reader = create_autospec(ScreeningReader, instance=True)
    showtime = datetime(2026, 6, 27, 19, 30, tzinfo=UTC)
    reader.find_by_id.return_value = ScreeningReader.ScreeningData(
        id="scr-1",
        movie_id="mov-1",
        movie_title="The Odyssey",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime=showtime,
        ticket_url="https://cinema.example/tickets/scr-1",
        room="Room 2",
        language="V.O.",
    )

    result = await GetScreeningQuery(screening_reader=reader).execute(
        GetScreeningQuery.InputData(screening_id="scr-1")
    )

    assert result == GetScreeningQuery.OutputData(
        id="scr-1",
        movie_id="mov-1",
        movie_title="The Odyssey",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime=showtime,
        ticket_url="https://cinema.example/tickets/scr-1",
        room="Room 2",
        language="V.O.",
    )
    reader.find_by_id.assert_awaited_once_with("scr-1")
    reader.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_screening_raises_application_error() -> None:
    """A missing projection becomes the public screening-not-found error."""
    reader = create_autospec(ScreeningReader, instance=True)
    reader.find_by_id.return_value = None

    with pytest.raises(
        ScreeningNotFoundError, match="A screening with ID 'missing' was not found"
    ):
        await GetScreeningQuery(screening_reader=reader).execute(
            GetScreeningQuery.InputData(screening_id="missing")
        )

    reader.find_by_id.assert_awaited_once_with("missing")
    reader.search.assert_not_awaited()


@pytest.mark.parametrize("screening_id", ["", " ", "\t\n"])
def test_input_rejects_blank_screening_id(screening_id: str) -> None:
    """Blank identifiers are rejected before the reader can be invoked."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        GetScreeningQuery.InputData(screening_id=screening_id)
