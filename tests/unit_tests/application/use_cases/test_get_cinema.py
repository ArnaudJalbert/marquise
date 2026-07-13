"""Tests for GetCinemaUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


@pytest.mark.asyncio
async def test_get_cinema_returns_cinema() -> None:
    """The use case maps a found cinema to its output data."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_by_id.return_value = Cinema(
        id=CinemaId(value="cin-1"),
        name="Cinema One",
        address="123 Rue Sainte-Catherine",
        city="Montréal",
        website="https://cinemaone.example.com",
    )

    use_case = GetCinemaUseCase(cinema_repository=mock_repo)
    result = await use_case.execute(GetCinemaUseCase.InputData(cinema_id="cin-1"))

    assert result.id == "cin-1"
    assert result.name == "Cinema One"
    assert result.address == "123 Rue Sainte-Catherine"
    assert result.city == "Montréal"
    assert result.website == "https://cinemaone.example.com"
    mock_repo.find_by_id.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_cinema_raises_when_missing() -> None:
    """The use case raises CinemaNotFoundError when the repo returns None."""
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_by_id.return_value = None

    use_case = GetCinemaUseCase(cinema_repository=mock_repo)
    with pytest.raises(CinemaNotFoundError):
        await use_case.execute(GetCinemaUseCase.InputData(cinema_id="missing"))


def test_get_cinema_input_rejects_empty_id() -> None:
    """Empty cinema_id is rejected at input validation."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        GetCinemaUseCase.InputData(cinema_id="  ")
