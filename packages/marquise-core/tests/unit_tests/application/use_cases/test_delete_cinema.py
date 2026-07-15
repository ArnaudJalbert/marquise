"""Tests for DeleteCinemaUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases import DeleteCinemaUseCase
from marquise.domain.value_objects import CinemaId


@pytest.mark.asyncio
async def test_delete_cinema_deletes_and_returns_id() -> None:
    """Verify the happy path: cinema is deleted and its ID is returned."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.delete.return_value = True

    use_case = DeleteCinemaUseCase(cinema_repository=mock_repo)
    request = DeleteCinemaUseCase.InputData(cinema_id="cin-001")

    response = await use_case.execute(request)

    assert response.cinema_id == "cin-001"
    mock_repo.delete.assert_awaited_once_with(cinema_id=CinemaId(value="cin-001"))


@pytest.mark.asyncio
async def test_delete_cinema_raises_not_found_when_cinema_missing() -> None:
    """Verify deleting a non-existent cinema raises CinemaNotFoundError."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.delete.return_value = False

    use_case = DeleteCinemaUseCase(cinema_repository=mock_repo)
    request = DeleteCinemaUseCase.InputData(cinema_id="cin-missing")

    with pytest.raises(CinemaNotFoundError, match="cin-missing"):
        await use_case.execute(request)

    mock_repo.delete.assert_awaited_once_with(cinema_id=CinemaId(value="cin-missing"))
