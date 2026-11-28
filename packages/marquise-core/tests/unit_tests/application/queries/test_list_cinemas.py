"""Tests for ListCinemasQuery."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.page import Page
from marquise.application.queries.list_cinemas import ListCinemasQuery
from marquise.application.readers import CinemaReader


@pytest.fixture
def cinema_reader() -> CinemaReader:
    """A cinema reader that returns an empty page."""
    cinema_reader = create_autospec(CinemaReader, instance=True)
    cinema_reader.search.return_value = Page(items=[], total=0)
    return cinema_reader


@pytest.fixture
def query(cinema_reader: CinemaReader) -> ListCinemasQuery:
    """The query under test, wired to the mocked reader."""
    return ListCinemasQuery(cinema_reader=cinema_reader)


@pytest.mark.asyncio
async def test_list_cinemas_returns_all_when_no_filter(
    query: ListCinemasQuery, cinema_reader: CinemaReader
) -> None:
    """Verify all cinemas are returned when no name filter is provided."""
    cinema_reader.search.return_value = Page(
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

    response = await query.execute(query.InputData(page=1, size=10))

    assert [(c.id, c.name) for c in response.cinemas] == [
        ("id-1", "Cinema A"),
        ("id-2", "Cinema B"),
    ]
    assert response.total == 2
    cinema_reader.search.assert_awaited_once_with(name_filter=None, limit=10, offset=0)


@pytest.mark.asyncio
async def test_list_cinemas_passes_page_and_size_as_limit_offset(
    query: ListCinemasQuery, cinema_reader: CinemaReader
) -> None:
    """Verify page/size are converted to limit/offset for the reader.

    Page 2, size 5 should produce limit=5, offset=5.
    """
    await query.execute(query.InputData(page=2, size=5))

    cinema_reader.search.assert_awaited_once_with(name_filter=None, limit=5, offset=5)


@pytest.mark.asyncio
async def test_list_cinemas_filters_by_name(
    query: ListCinemasQuery, cinema_reader: CinemaReader
) -> None:
    """Verify the name filter is passed to the reader."""
    cinema_reader.search.return_value = Page(
        items=[CinemaReader.CinemaData(id="id-1", name="Cinema A")], total=1
    )

    response = await query.execute(query.InputData(name="Cinema A", page=1, size=10))

    assert [c.name for c in response.cinemas] == ["Cinema A"]
    cinema_reader.search.assert_awaited_once_with(
        name_filter="Cinema A", limit=10, offset=0
    )


@pytest.mark.asyncio
async def test_list_cinemas_returns_empty_list_when_no_matches(
    query: ListCinemasQuery,
) -> None:
    """Verify an empty list is returned when no cinemas match the filter."""
    response = await query.execute(query.InputData(name="NonExistent", page=1, size=10))

    assert response.cinemas == []
    assert response.total == 0


@pytest.mark.asyncio
async def test_list_cinemas_maps_all_fields_correctly(
    query: ListCinemasQuery, cinema_reader: CinemaReader
) -> None:
    """Verify every reader field is mapped to CinemaData."""
    cinema_reader.search.return_value = Page(
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

    response = await query.execute(query.InputData(page=1, size=10))

    assert response.cinemas == [
        query.CinemaData(
            id="id-1",
            name="Full Cinema",
            address="789 Full St",
            city="Quebec City",
            website="https://full-cinema.example.com",
        )
    ]


@pytest.mark.asyncio
async def test_list_cinemas_maps_optional_none_fields(
    query: ListCinemasQuery, cinema_reader: CinemaReader
) -> None:
    """Verify optional fields stay None when the reader has none."""
    cinema_reader.search.return_value = Page(
        items=[CinemaReader.CinemaData(id="id-1", name="Minimal")], total=1
    )

    response = await query.execute(query.InputData(page=1, size=10))

    assert response.cinemas == [query.CinemaData(id="id-1", name="Minimal")]


@pytest.mark.asyncio
async def test_list_cinemas_output_total_reflects_reader_total(
    query: ListCinemasQuery, cinema_reader: CinemaReader
) -> None:
    """The output's total reflects the reader's total, not the page size."""
    cinema_reader.search.return_value = Page(
        items=[CinemaReader.CinemaData(id="id-1", name="Cinema A")], total=50
    )

    response = await query.execute(query.InputData(size=1, page=1))

    assert len(response.cinemas) == 1
    assert response.total == 50


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("page", "size", "name", "message"),
    [
        (0, 10, None, "page must be at least 1"),
        (1, 0, None, "size must be positive"),
        (1, 10, "", "name must not be empty when provided"),
        (1, 10, "   ", "name must not be empty when provided"),
    ],
    ids=["page-below-one", "zero-size", "empty-name", "whitespace-name"],
)
async def test_list_cinemas_rejects_invalid_input_before_reading(
    query: ListCinemasQuery,
    cinema_reader: CinemaReader,
    page: int,
    size: int,
    name: str | None,
    message: str,
) -> None:
    """Invalid page, size or name fails before the reader is called."""
    with pytest.raises(ValueError, match=message):
        await query.execute(query.InputData(page=page, size=size, name=name))

    cinema_reader.search.assert_not_awaited()
