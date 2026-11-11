"""Tests for CreateCinemaUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
)
from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


@pytest.mark.asyncio
async def test_create_cinema_saves_and_returns_response() -> None:
    """Verify the happy path: cinema is saved and response data is correct."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_by_name_and_address.return_value = None
    mock_repo.save.return_value = Cinema(
        id=CinemaId(value="550e8400-e29b-41d4-a716-446655440000"),
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )

    use_case = CreateCinemaUseCase(cinema_repository=mock_repo)
    request = CreateCinemaUseCase.InputData(
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )

    response = await use_case.execute(request)

    assert response.id == "550e8400-e29b-41d4-a716-446655440000"
    assert response.name == "Test Cinema"
    assert response.address == "123 Test St"
    assert response.city == "Montreal"
    assert response.website == "https://example.com"
    mock_repo.find_by_name_and_address.assert_awaited_once_with(
        name="Test Cinema", address="123 Test St"
    )
    mock_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_cinema_raises_error_when_cinema_already_exists() -> None:
    """Verify duplicate name+address raises CinemaAlreadyExistsError."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    existing = Cinema(
        id=CinemaId(value="550e8400-e29b-41d4-a716-446655440000"),
        name="Existing Cinema",
        address="123 Test St",
        city="Montreal",
    )
    mock_repo.find_by_name_and_address.return_value = existing

    use_case = CreateCinemaUseCase(cinema_repository=mock_repo)
    request = CreateCinemaUseCase.InputData(
        name="Existing Cinema", address="123 Test St", city="Montreal"
    )

    with pytest.raises(CinemaAlreadyExistsError, match="already exists"):
        await use_case.execute(request)

    mock_repo.find_by_name_and_address.assert_awaited_once()
    mock_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_cinema_raises_error_when_id_collision() -> None:
    """Verify a UUID collision during save raises CinemaIdAlreadyExistsError."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_by_name_and_address.return_value = None
    mock_repo.save.side_effect = CinemaIdAlreadyExistsError(
        "A cinema with ID '550e8400-e29b-41d4-a716-446655440000' already exists"
    )

    use_case = CreateCinemaUseCase(cinema_repository=mock_repo)
    request = CreateCinemaUseCase.InputData(
        name="Test Cinema", address="123 Test St", city="Montreal"
    )

    with pytest.raises(CinemaIdAlreadyExistsError, match="already exists"):
        await use_case.execute(request)

    mock_repo.find_by_name_and_address.assert_awaited_once()
    mock_repo.save.assert_awaited_once()
