"""Tests for ListCinemasUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases import ListCinemasUseCase
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


@pytest.mark.asyncio
async def test_list_cinemas_returns_all_when_no_filter() -> None:
    """Verify all cinemas are returned when no name filter is provided."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = [
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
    ]

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData()

    response = await use_case.execute(request)

    assert len(response.cinemas) == 2
    assert response.cinemas[0].id == "id-1"
    assert response.cinemas[0].name == "Cinema A"
    assert response.cinemas[1].id == "id-2"
    assert response.cinemas[1].name == "Cinema B"
    mock_repo.find_all.assert_awaited_once_with(name_filter=None)


@pytest.mark.asyncio
async def test_list_cinemas_filters_by_name() -> None:
    """Verify cinemas are filtered when a name filter is provided."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = [
        Cinema(
            id=CinemaId(value="id-1"),
            name="Cinema A",
            address="123 A St",
            city="Montreal",
        ),
    ]

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData(name="Cinema A")

    response = await use_case.execute(request)

    assert len(response.cinemas) == 1
    assert response.cinemas[0].name == "Cinema A"
    mock_repo.find_all.assert_awaited_once_with(name_filter="Cinema A")


@pytest.mark.asyncio
async def test_list_cinemas_returns_empty_list_when_no_matches() -> None:
    """Verify an empty list is returned when no cinemas match the filter."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = []

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData(name="NonExistent")

    response = await use_case.execute(request)

    assert len(response.cinemas) == 0
    mock_repo.find_all.assert_awaited_once_with(name_filter="NonExistent")


@pytest.mark.asyncio
async def test_list_cinemas_maps_all_fields_correctly() -> None:
    """Verify all cinema fields are mapped to CinemaData."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_all.return_value = [
        Cinema(
            id=CinemaId(value="id-1"),
            name="Full Cinema",
            address="789 Full St",
            city="Quebec City",
            website="https://full-cinema.example.com",
        ),
    ]

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
    mock_repo.find_all.return_value = [
        Cinema(
            id=CinemaId(value="id-1"),
            name="Minimal Cinema",
        ),
    ]

    use_case = ListCinemasUseCase(cinema_repository=mock_repo)
    request = ListCinemasUseCase.InputData()

    response = await use_case.execute(request)

    cinema = response.cinemas[0]
    assert cinema.id == "id-1"
    assert cinema.name == "Minimal Cinema"
    assert cinema.address is None
    assert cinema.city is None
    assert cinema.website is None
