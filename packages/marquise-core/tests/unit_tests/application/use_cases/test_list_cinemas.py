"""Tests for ListCinemasUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import CinemaRepository, Page
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


@pytest.mark.asyncio
async def test_list_cinemas_returns_all_when_no_filter() -> None:
    """Verify all cinemas are returned when no name filter is provided."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[
            Cinema(
                id=CinemaId(value="id-1"),
                name="Cinema A",
                address="123 A St",
                city="Montreal",
            ),
            Cinema(
                id=CinemaId(value="id-2"),
                name="Cinema B",
                address="456 B St",
                city="Montreal",
            ),
        ],
        total=2,
    )

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData()

    response = await use_case.execute(request)

    assert len(response.cinemas) == 2
    assert response.cinemas[0].id == "id-1"
    assert response.cinemas[0].name == "Cinema A"
    assert response.cinemas[1].id == "id-2"
    assert response.cinemas[1].name == "Cinema B"
    assert response.total == 2
    mock_repo.find_all.assert_awaited_once_with(name_filter=None, limit=None, offset=0)


@pytest.mark.asyncio
async def test_list_cinemas_passes_page_and_size_as_limit_offset() -> None:
    """Verify page/size are converted to limit/offset for the repository.

    Page 2, size 5 should produce limit=5, offset=5.
    """
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = Page(items=[], total=50)

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData(page=2, size=5)

    await use_case.execute(request)

    mock_repo.find_all.assert_awaited_once_with(name_filter=None, limit=5, offset=5)


@pytest.mark.asyncio
async def test_list_cinemas_filters_by_name() -> None:
    """Verify cinemas are filtered when a name filter is provided."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[
            Cinema(
                id=CinemaId(value="id-1"),
                name="Cinema A",
                address="123 A St",
                city="Montreal",
            ),
        ],
        total=1,
    )

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData(name="Cinema A")

    response = await use_case.execute(request)

    assert len(response.cinemas) == 1
    assert response.cinemas[0].name == "Cinema A"
    mock_repo.find_all.assert_awaited_once_with(
        name_filter="Cinema A", limit=None, offset=0
    )


@pytest.mark.asyncio
async def test_list_cinemas_returns_empty_list_when_no_matches() -> None:
    """Verify an empty list is returned when no cinemas match the filter."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = Page(items=[], total=0)

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData(name="NonExistent")

    response = await use_case.execute(request)

    assert len(response.cinemas) == 0
    assert response.total == 0
    mock_repo.find_all.assert_awaited_once_with(
        name_filter="NonExistent", limit=None, offset=0
    )


@pytest.mark.asyncio
async def test_list_cinemas_maps_all_fields_correctly() -> None:
    """Verify all cinema fields are mapped to CinemaData."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[
            Cinema(
                id=CinemaId(value="id-1"),
                name="Full Cinema",
                address="789 Full St",
                city="Quebec City",
                website="https://full-cinema.example.com",
            ),
        ],
        total=1,
    )

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData()

    response = await use_case.execute(request)

    cinema = response.cinemas[0]
    assert cinema.id == "id-1"
    assert cinema.name == "Full Cinema"
    assert cinema.address == "789 Full St"
    assert cinema.city == "Quebec City"
    assert cinema.website == "https://full-cinema.example.com"


@pytest.mark.asyncio
async def test_list_cinemas_maps_optional_none_fields() -> None:
    """Verify optional fields are None when the entity has them as None."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[
            Cinema(
                id=CinemaId(value="id-1"),
                name="Minimal Cinema",
            ),
        ],
        total=1,
    )

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData()

    response = await use_case.execute(request)

    cinema = response.cinemas[0]
    assert cinema.id == "id-1"
    assert cinema.name == "Minimal Cinema"
    assert cinema.address is None
    assert cinema.city is None
    assert cinema.website is None


@pytest.mark.asyncio
async def test_list_cinemas_output_total_reflects_repository_total() -> None:
    """The output's total reflects the repository's total, not the page size."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[
            Cinema(id=CinemaId(value="id-1"), name="Cinema A"),
        ],
        total=50,
    )

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData(size=1)

    response = await use_case.execute(request)

    assert len(response.cinemas) == 1
    assert response.total == 50


@pytest.mark.asyncio
async def test_list_cinemas_rejects_page_below_one() -> None:
    """A page number less than 1 is rejected before the repository is called."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        ListCinemasUseCase.InputData(page=0)


@pytest.mark.asyncio
async def test_list_cinemas_rejects_zero_or_negative_size() -> None:
    """A non-positive size is rejected before the repository is called."""
    with pytest.raises(ValueError, match="size must be positive when provided"):
        ListCinemasUseCase.InputData(size=0)
