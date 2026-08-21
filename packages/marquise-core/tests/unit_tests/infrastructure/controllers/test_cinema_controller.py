"""Tests for CinemaController."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_screenings import (
    GetCinemaScreeningsUseCase,
)
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.controllers.cinema_controller import CinemaController


@pytest.fixture
def mock_list_use_case() -> ListCinemasUseCase:
    """Provide a mocked ListCinemasUseCase."""
    return create_autospec(ListCinemasUseCase, instance=True)


@pytest.fixture
def mock_update_use_case() -> UpdateCinemaUseCase:
    """Provide a mocked UpdateCinemaUseCase."""
    return create_autospec(UpdateCinemaUseCase, instance=True)


@pytest.fixture
def mock_get_use_case() -> GetCinemaUseCase:
    """Provide a mocked GetCinemaUseCase."""
    return create_autospec(GetCinemaUseCase, instance=True)


@pytest.fixture
def mock_get_movies_use_case() -> GetCinemaMoviesUseCase:
    """Provide a mocked GetCinemaMoviesUseCase."""
    return create_autospec(GetCinemaMoviesUseCase, instance=True)


@pytest.fixture
def mock_get_screenings_use_case() -> GetCinemaScreeningsUseCase:
    """Provide a mocked GetCinemaScreeningsUseCase."""
    return create_autospec(GetCinemaScreeningsUseCase, instance=True)


@pytest.fixture
def controller(
    mock_get_use_case: GetCinemaUseCase,
    mock_get_movies_use_case: GetCinemaMoviesUseCase,
    mock_get_screenings_use_case: GetCinemaScreeningsUseCase,
    mock_list_use_case: ListCinemasUseCase,
    mock_update_use_case: UpdateCinemaUseCase,
) -> CinemaController:
    """Provide a CinemaController wired to mocks."""
    return CinemaController(
        get_cinema_use_case=mock_get_use_case,
        get_cinema_movies_use_case=mock_get_movies_use_case,
        get_cinema_screenings_use_case=mock_get_screenings_use_case,
        list_cinemas_use_case=mock_list_use_case,
        update_cinema_use_case=mock_update_use_case,
    )


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_returns_cinemas(
    controller: CinemaController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list returns cinema data from the use case."""
    cinema_data = [
        ListCinemasUseCase.CinemaData(
            id="cin-001",
            name="Cinema du Parc",
            address="123 Rue du Parc",
            city="Montreal",
            website="https://cinemaduparc.ca",
        ),
        ListCinemasUseCase.CinemaData(
            id="cin-002",
            name="Quartier Latin",
            address="345 Rue Ontario",
            city="Montreal",
        ),
    ]
    expected = ListCinemasUseCase.OutputData(cinemas=cinema_data, total=2)
    mock_list_use_case.execute.return_value = expected

    result = await controller.list()

    assert result == expected
    assert len(result.cinemas) == 2
    mock_list_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_passes_name_filter(
    controller: CinemaController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list passes the name filter to the use case."""
    output = ListCinemasUseCase.OutputData(cinemas=[], total=0)
    mock_list_use_case.execute.return_value = output

    await controller.list(name="Parc")

    mock_list_use_case.execute.assert_awaited_once()
    input_data = mock_list_use_case.execute.call_args[0][0]
    assert isinstance(input_data, ListCinemasUseCase.InputData)
    assert input_data.name == "Parc"


@pytest.mark.asyncio
async def test_list_passes_page_and_size(
    controller: CinemaController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list passes page/size through to the use case."""
    output = ListCinemasUseCase.OutputData(cinemas=[], total=0)
    mock_list_use_case.execute.return_value = output

    await controller.list(page=2, size=5)

    mock_list_use_case.execute.assert_awaited_once()
    input_data = mock_list_use_case.execute.call_args[0][0]
    assert input_data.page == 2
    assert input_data.size == 5


# ---------------------------------------------------------------------------
# list_cinemas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_cinemas_delegates_to_use_case(
    controller: CinemaController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list_cinemas delegates to the use case."""
    cinema_data = [
        ListCinemasUseCase.CinemaData(
            id="cin-001",
            name="Cinema du Parc",
        ),
    ]
    expected = ListCinemasUseCase.OutputData(cinemas=cinema_data, total=1)
    mock_list_use_case.execute.return_value = expected

    result = await controller.list_cinemas(name_filter="Parc")

    assert result == expected
    mock_list_use_case.execute.assert_awaited_once()
    input_data = mock_list_use_case.execute.call_args[0][0]
    assert input_data.name == "Parc"
    assert input_data.page == 1
    assert input_data.size is None


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_delegates_to_use_case(
    controller: CinemaController,
    mock_update_use_case: UpdateCinemaUseCase,
) -> None:
    """Verify update delegates to the use case."""
    expected_output = UpdateCinemaUseCase.OutputData(
        id="cin-001",
        name="Updated Name",
        address="456 New Ave",
        city="Quebec",
        website="https://updated.example.com",
    )
    mock_update_use_case.execute.return_value = expected_output

    result = await controller.update(
        cinema_id="cin-001",
        name="Updated Name",
        address="456 New Ave",
        city="Quebec",
        website="https://updated.example.com",
    )

    assert result == expected_output
    mock_update_use_case.execute.assert_awaited_once()
    input_data = mock_update_use_case.execute.call_args[0][0]
    assert isinstance(input_data, UpdateCinemaUseCase.InputData)
    assert input_data.cinema_id == "cin-001"
    assert input_data.name == "Updated Name"
    assert input_data.address == "456 New Ave"
    assert input_data.city == "Quebec"
    assert input_data.website == "https://updated.example.com"
