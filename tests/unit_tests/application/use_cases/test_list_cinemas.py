"""Tests for ListCinemasUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import CinemaRepository, Page
from marquise.application.use_cases import ListCinemasUseCase
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
async def test_list_cinemas_passes_limit_and_offset_to_repository() -> None:
    """Verify limit/offset are forwarded to the repository unchanged."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = Page(items=[], total=50)

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData(limit=5, offset=10)

    await use_case.execute(request)

    mock_repo.find_all.assert_awaited_once_with(name_filter=None, limit=5, offset=10)


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
    request = ListCinemasUseCase.InputData(limit=1)

    response = await use_case.execute(request)

    assert len(response.cinemas) == 1
    assert response.total == 50


@pytest.mark.asyncio
async def test_list_cinemas_rejects_negative_offset() -> None:
    """A negative offset is rejected before the repository is called."""
    with pytest.raises(ValueError, match="offset must not be negative"):
        ListCinemasUseCase.InputData(offset=-1)


@pytest.mark.asyncio
async def test_list_cinemas_rejects_zero_or_negative_limit() -> None:
    """A non-positive limit is rejected before the repository is called."""
    with pytest.raises(ValueError, match="limit must be positive"):
        ListCinemasUseCase.InputData(limit=0)
