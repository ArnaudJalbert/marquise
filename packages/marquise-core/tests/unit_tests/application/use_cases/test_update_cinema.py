"""Tests for UpdateCinemaUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


@pytest.mark.asyncio
async def test_update_cinema_updates_and_returns_response() -> None:
    """Verify the happy path: cinema is updated and response data is correct."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.update.return_value = Cinema(
        id=CinemaId(value="cin-001"),
        name="Updated Name",
        address="456 New Ave",
        city="Quebec",
        website="https://new.example.com",
    )

    use_case = UpdateCinemaUseCase(cinema_repository=mock_repo)
    request = UpdateCinemaUseCase.InputData(
        cinema_id="cin-001",
        name="Updated Name",
        address="456 New Ave",
        city="Quebec",
        website="https://new.example.com",
    )

    response = await use_case.execute(request)

    assert response.id == "cin-001"
    assert response.name == "Updated Name"
    assert response.address == "456 New Ave"
    assert response.city == "Quebec"
    assert response.website == "https://new.example.com"
    mock_repo.update.assert_awaited_once_with(
        Cinema(
            id=CinemaId(value="cin-001"),
            name="Updated Name",
            address="456 New Ave",
            city="Quebec",
            website="https://new.example.com",
        )
    )


@pytest.mark.asyncio
async def test_update_cinema_raises_not_found_when_cinema_missing() -> None:
    """Verify updating a non-existent cinema raises CinemaNotFoundError."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.update.return_value = None

    use_case = UpdateCinemaUseCase(cinema_repository=mock_repo)
    request = UpdateCinemaUseCase.InputData(
        cinema_id="cin-missing",
        name="Updated Name",
        address="456 New Ave",
        city="Quebec",
    )

    with pytest.raises(CinemaNotFoundError, match="cin-missing"):
        await use_case.execute(request)

    mock_repo.update.assert_awaited_once()
