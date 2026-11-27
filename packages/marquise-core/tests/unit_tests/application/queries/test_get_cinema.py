"""Tests for GetCinemaQuery."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.queries.get_cinema import GetCinemaQuery
from marquise.application.readers import CinemaReader


@pytest.fixture
def cinema_reader() -> CinemaReader:
    """Provide a reader that finds one cinema."""
    cinema_reader = create_autospec(CinemaReader, instance=True)
    cinema_reader.find_by_id.return_value = CinemaReader.CinemaData(
        id="cin-1",
        name="Cinema One",
        address="123 Rue Sainte-Catherine",
        city="Montréal",
        website="https://cinemaone.example.com",
    )
    return cinema_reader


@pytest.fixture
def query(cinema_reader: CinemaReader) -> GetCinemaQuery:
    """Provide the query over the mocked reader."""
    return GetCinemaQuery(cinema_reader=cinema_reader)


@pytest.mark.asyncio
async def test_get_cinema_returns_cinema(
    query: GetCinemaQuery, cinema_reader: CinemaReader
) -> None:
    """The query maps the reader's cinema to its output data."""
    result = await query.execute(query.InputData(cinema_id="cin-1"))

    assert result == GetCinemaQuery.OutputData(
        id="cin-1",
        name="Cinema One",
        address="123 Rue Sainte-Catherine",
        city="Montréal",
        website="https://cinemaone.example.com",
    )
    cinema_reader.find_by_id.assert_awaited_once_with("cin-1")


@pytest.mark.asyncio
async def test_get_cinema_raises_when_missing(
    query: GetCinemaQuery, cinema_reader: CinemaReader
) -> None:
    """The query raises CinemaNotFoundError when the reader finds nothing."""
    cinema_reader.find_by_id.return_value = None

    with pytest.raises(CinemaNotFoundError):
        await query.execute(query.InputData(cinema_id="missing"))


def test_get_cinema_input_rejects_empty_id() -> None:
    """Empty cinema_id is rejected at input validation."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        GetCinemaQuery.InputData(cinema_id="  ")
