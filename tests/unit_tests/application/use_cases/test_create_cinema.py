"""Tests for CreateCinemaUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.dtos.cinema import CreateCinemaRequest
from marquise.application.exceptions import CinemaIdAlreadyExistsError
from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases import CreateCinemaUseCase
from marquise.domain.entities import Cinema
from marquise.domain.exceptions import CinemaAlreadyExistsError
from marquise.domain.value_objects import CinemaId


@pytest.mark.asyncio
async def test_create_cinema_saves_and_returns_response() -> None:
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_by_name_and_address.return_value = None
    mock_repo.exists_by_id.return_value = False
    mock_repo.save.return_value = Cinema(
        id=CinemaId(value="550e8400-e29b-41d4-a716-446655440000"),
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
    )

    use_case = CreateCinemaUseCase(cinema_repository=mock_repo)
    request = CreateCinemaRequest(
        name="Test Cinema", address="123 Test St", city="Montreal"
    )

    response = await use_case.execute(request)

    assert response.id == "550e8400-e29b-41d4-a716-446655440000"
    assert response.name == "Test Cinema"
    assert response.address == "123 Test St"
    assert response.city == "Montreal"
    mock_repo.find_by_name_and_address.assert_awaited_once_with(
        name="Test Cinema", address="123 Test St"
    )
    mock_repo.exists_by_id.assert_awaited_once()
    mock_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_cinema_raises_error_when_cinema_already_exists() -> None:
    mock_repo = create_autospec(CinemaRepository, instance=True)
    existing = Cinema(
        id=CinemaId(value="550e8400-e29b-41d4-a716-446655440000"),
        name="Existing Cinema",
        address="123 Test St",
        city="Montreal",
    )
    mock_repo.find_by_name_and_address.return_value = existing

    use_case = CreateCinemaUseCase(cinema_repository=mock_repo)
    request = CreateCinemaRequest(
        name="Existing Cinema", address="123 Test St", city="Montreal"
    )

    with pytest.raises(CinemaAlreadyExistsError, match="already exists"):
        await use_case.execute(request)

    mock_repo.find_by_name_and_address.assert_awaited_once()
    mock_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_cinema_raises_error_when_id_collision() -> None:
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_by_name_and_address.return_value = None
    mock_repo.exists_by_id.return_value = True

    use_case = CreateCinemaUseCase(cinema_repository=mock_repo)
    request = CreateCinemaRequest(
        name="Test Cinema", address="123 Test St", city="Montreal"
    )

    with pytest.raises(CinemaIdAlreadyExistsError, match="already exists"):
        await use_case.execute(request)

    mock_repo.find_by_name_and_address.assert_awaited_once()
    mock_repo.exists_by_id.assert_awaited_once()
    mock_repo.save.assert_not_awaited()
