"""Tests for ListCinemasQuery."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.page import Page
from marquise.application.queries.list_cinemas import ListCinemasQuery
from marquise.application.readers import CinemaReader


def _reader(page: Page[CinemaReader.CinemaData]) -> CinemaReader:
    """Build a cinema reader mock that returns one page."""
    reader = create_autospec(CinemaReader, instance=True)
    reader.search.return_value = page
    return reader


@pytest.mark.asyncio
async def test_list_cinemas_returns_all_when_no_filter() -> None:
    """Verify all cinemas are returned when no name filter is provided."""
    reader = _reader(
        Page(
            items=[
                CinemaReader.CinemaData(
                    id="id-1", name="Cinema A", address="123 A St", city="Montreal"
                ),
                CinemaReader.CinemaData(
                    id="id-2", name="Cinema B", address="456 B St", city="Montreal"
                ),
            ],
            total=2,
        )
    )

    query = ListCinemasQuery(cinema_reader=reader)
    response = await query.execute(ListCinemasQuery.InputData(page=1, size=10))

    assert [(c.id, c.name) for c in response.cinemas] == [
        ("id-1", "Cinema A"),
        ("id-2", "Cinema B"),
    ]
    assert response.total == 2
    reader.search.assert_awaited_once_with(name_filter=None, limit=10, offset=0)


@pytest.mark.asyncio
async def test_list_cinemas_passes_page_and_size_as_limit_offset() -> None:
    """Verify page/size are converted to limit/offset for the reader.

    Page 2, size 5 should produce limit=5, offset=5.
    """
    reader = _reader(Page(items=[], total=50))

    query = ListCinemasQuery(cinema_reader=reader)
    await query.execute(ListCinemasQuery.InputData(page=2, size=5))

    reader.search.assert_awaited_once_with(name_filter=None, limit=5, offset=5)


@pytest.mark.asyncio
async def test_list_cinemas_filters_by_name() -> None:
    """Verify the name filter is passed to the reader."""
    reader = _reader(
        Page(items=[CinemaReader.CinemaData(id="id-1", name="Cinema A")], total=1)
    )

    query = ListCinemasQuery(cinema_reader=reader)
    response = await query.execute(
        ListCinemasQuery.InputData(name="Cinema A", page=1, size=10)
    )

    assert [c.name for c in response.cinemas] == ["Cinema A"]
    reader.search.assert_awaited_once_with(name_filter="Cinema A", limit=10, offset=0)


@pytest.mark.asyncio
async def test_list_cinemas_returns_empty_list_when_no_matches() -> None:
    """Verify an empty list is returned when no cinemas match the filter."""
    reader = _reader(Page(items=[], total=0))

    query = ListCinemasQuery(cinema_reader=reader)
    response = await query.execute(
        ListCinemasQuery.InputData(name="NonExistent", page=1, size=10)
    )

    assert response.cinemas == []
    assert response.total == 0


@pytest.mark.asyncio
async def test_list_cinemas_maps_all_fields_correctly() -> None:
    """Verify every reader field is mapped to CinemaData."""
    reader = _reader(
        Page(
            items=[
                CinemaReader.CinemaData(
                    id="id-1",
                    name="Full Cinema",
                    address="789 Full St",
                    city="Quebec City",
                    website="https://full-cinema.example.com",
                )
            ],
            total=1,
        )
    )

    query = ListCinemasQuery(cinema_reader=reader)
    response = await query.execute(ListCinemasQuery.InputData(page=1, size=10))

    assert response.cinemas == [
        ListCinemasQuery.CinemaData(
            id="id-1",
            name="Full Cinema",
            address="789 Full St",
            city="Quebec City",
            website="https://full-cinema.example.com",
        )
    ]


@pytest.mark.asyncio
async def test_list_cinemas_maps_optional_none_fields() -> None:
    """Verify optional fields stay None when the reader has none."""
    reader = _reader(
        Page(items=[CinemaReader.CinemaData(id="id-1", name="Minimal")], total=1)
    )

    query = ListCinemasQuery(cinema_reader=reader)
    response = await query.execute(ListCinemasQuery.InputData(page=1, size=10))

    assert response.cinemas == [ListCinemasQuery.CinemaData(id="id-1", name="Minimal")]


@pytest.mark.asyncio
async def test_list_cinemas_output_total_reflects_reader_total() -> None:
    """The output's total reflects the reader's total, not the page size."""
    reader = _reader(
        Page(items=[CinemaReader.CinemaData(id="id-1", name="Cinema A")], total=50)
    )

    query = ListCinemasQuery(cinema_reader=reader)
    response = await query.execute(ListCinemasQuery.InputData(size=1, page=1))

    assert len(response.cinemas) == 1
    assert response.total == 50


def test_list_cinemas_rejects_page_below_one() -> None:
    """A page number less than 1 is rejected before the reader is called."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        ListCinemasQuery.InputData(page=0, size=10)


def test_list_cinemas_rejects_zero_or_negative_size() -> None:
    """A non-positive size is rejected before the reader is called."""
    with pytest.raises(ValueError, match="size must be positive"):
        ListCinemasQuery.InputData(size=0, page=1)
