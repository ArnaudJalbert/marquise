"""Tests for GetCinemaSourceQuery."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaSourceAssignmentNotFoundError
from marquise.application.queries.get_cinema_source import GetCinemaSourceQuery
from marquise.application.readers import CinemaSourceAssignmentReader


@pytest.fixture
def reader() -> CinemaSourceAssignmentReader:
    """Provide a reader that finds the cin-001 assignment."""
    reader = create_autospec(CinemaSourceAssignmentReader, instance=True)
    reader.find_by_cinema_id.return_value = (
        CinemaSourceAssignmentReader.CinemaSourceAssignmentData(
            cinema_id="cin-001",
            source_name="cineplex",
            source_display_name="Cineplex",
        )
    )
    return reader


@pytest.fixture
def query(reader: CinemaSourceAssignmentReader) -> GetCinemaSourceQuery:
    """Provide the query over the mocked reader."""
    return GetCinemaSourceQuery(reader)


@pytest.mark.asyncio
async def test_get_cinema_source_returns_assignment(
    query: GetCinemaSourceQuery, reader: CinemaSourceAssignmentReader
) -> None:
    """An assigned cinema returns its source name and display name."""
    response = await query.execute(query.InputData(cinema_id="cin-001"))

    assert response == GetCinemaSourceQuery.OutputData(
        cinema_id="cin-001",
        source_name="cineplex",
        source_display_name="Cineplex",
    )
    reader.find_by_cinema_id.assert_awaited_once_with("cin-001")


@pytest.mark.asyncio
async def test_get_cinema_source_raises_not_found(
    query: GetCinemaSourceQuery, reader: CinemaSourceAssignmentReader
) -> None:
    """A cinema without an assignment raises instead of returning output."""
    reader.find_by_cinema_id.return_value = None

    with pytest.raises(
        CinemaSourceAssignmentNotFoundError, match="No source assignment found"
    ):
        await query.execute(query.InputData(cinema_id="cin-001"))


@pytest.mark.parametrize("cinema_id", ["", "   "])
def test_input_data_rejects_blank_cinema_id(cinema_id: str) -> None:
    """An empty or whitespace-only cinema ID fails before any read."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        GetCinemaSourceQuery.InputData(cinema_id=cinema_id)


def test_input_data_rejects_non_string_cinema_id() -> None:
    """A cinema ID that is not a string fails with a type error."""
    with pytest.raises(TypeError, match="cinema_id must be a string"):
        GetCinemaSourceQuery.InputData(cinema_id=1)  # type: ignore[arg-type]
