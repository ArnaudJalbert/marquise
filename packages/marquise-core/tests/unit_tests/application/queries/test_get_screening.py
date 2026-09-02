"""Tests for GetScreeningQuery."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.queries.get_screening import GetScreeningQuery
from marquise.application.readers import ScreeningReader


@pytest.mark.asyncio
async def test_returns_screening_when_found() -> None:
    """Query returns reader projection as local output data."""
    reader = create_autospec(ScreeningReader, instance=True)
    reader.get_by_id.return_value = ScreeningReader.ScreeningData(
        id="scr-1",
        movie_id="mov-1",
        movie_title="The Odyssey",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
    )

    query = GetScreeningQuery(screening_reader=reader)
    result = await query.execute(GetScreeningQuery.InputData(screening_id="scr-1"))

    assert result.id == "scr-1"
    assert result.movie_id == "mov-1"
    assert result.movie_title == "The Odyssey"
    assert result.cinema_id == "cin-1"
    assert result.cinema_name == "Cinema One"
    assert result.showtime == datetime(2026, 6, 27, 19, 30, tzinfo=UTC)
    reader.get_by_id.assert_awaited_once_with("scr-1")


@pytest.mark.asyncio
async def test_raises_when_screening_missing() -> None:
    """Missing reader projection raises ScreeningNotFoundError."""
    reader = create_autospec(ScreeningReader, instance=True)
    reader.get_by_id.return_value = None

    query = GetScreeningQuery(screening_reader=reader)
    with pytest.raises(ScreeningNotFoundError, match="missing"):
        await query.execute(GetScreeningQuery.InputData(screening_id="missing"))


def test_input_rejects_empty_screening_id() -> None:
    """Empty screening_id is rejected."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        GetScreeningQuery.InputData(screening_id="  ")
