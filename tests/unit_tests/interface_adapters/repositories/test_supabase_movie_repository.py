"""Tests for SupabaseMovieRepository."""

from __future__ import annotations

from datetime import date
from unittest.mock import create_autospec

import pytest

from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from marquise.interface_adapters.repositories.protocols.movie import MovieGateway
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)


@pytest.fixture
def sample_movie() -> Movie:
    """Provide a sample Movie for tests."""
    return Movie(
        id=MovieId(value="mov-123"),
        title="Inception",
        release_date=date(2010, 7, 16),
        directors=("Christopher Nolan",),
        cast=("Leonardo DiCaprio", "Joseph Gordon-Levitt"),
        duration_minutes=148,
        description="A thief who steals corporate secrets...",
    )


@pytest.fixture
def gateway_dict() -> dict:
    """Provide a sample gateway return dict."""
    return {
        "id": "mov-123",
        "title": "Inception",
        "release_date": date(2010, 7, 16),
        "directors": "Christopher Nolan",
        "cast_members": "Leonardo DiCaprio,Joseph Gordon-Levitt",
        "duration_minutes": 148,
        "description": "A thief who steals corporate secrets...",
    }


@pytest.mark.asyncio
async def test_save(sample_movie: Movie) -> None:
    """Test save delegates to gateway and maps result."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.save.return_value = {
        "id": "mov-123",
        "title": "Inception",
        "release_date": date(2010, 7, 16),
        "directors": "Christopher Nolan",
        "cast_members": "Leonardo DiCaprio,Joseph Gordon-Levitt",
        "duration_minutes": 148,
        "description": "A thief who steals corporate secrets...",
    }

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.save(sample_movie)

    assert result.id == MovieId(value="mov-123")
    assert result.title == "Inception"
    assert result.directors == ("Christopher Nolan",)
    assert result.cast == ("Leonardo DiCaprio", "Joseph Gordon-Levitt")
    assert result.duration_minutes == 148
    mock_gateway.save.assert_awaited_once_with(
        movie_id="mov-123",
        title="Inception",
        release_date=date(2010, 7, 16),
        directors="Christopher Nolan",
        cast="Leonardo DiCaprio,Joseph Gordon-Levitt",
        duration_minutes=148,
        description="A thief who steals corporate secrets...",
    )


@pytest.mark.asyncio
async def test_find_by_id(gateway_dict: dict) -> None:
    """Test find_by_id returns entity when found."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_by_id.return_value = gateway_dict

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.find_by_id(MovieId(value="mov-123"))

    assert result is not None
    assert result.id == MovieId(value="mov-123")
    assert result.title == "Inception"
    mock_gateway.find_by_id.assert_awaited_once_with(movie_id="mov-123")


@pytest.mark.asyncio
async def test_find_by_id_missing() -> None:
    """Test find_by_id returns None when not found."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_by_id.return_value = None

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.find_by_id(MovieId(value="mov-999"))

    assert result is None


@pytest.mark.asyncio
async def test_find_by_title(gateway_dict: dict) -> None:
    """Test find_by_title returns entity when found."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_by_title.return_value = gateway_dict

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.find_by_title("Inception")

    assert result is not None
    assert result.title == "Inception"
    assert result.id == MovieId(value="mov-123")
    mock_gateway.find_by_title.assert_awaited_once_with(title="Inception")


@pytest.mark.asyncio
async def test_find_by_title_missing() -> None:
    """Test find_by_title returns None when not found."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_by_title.return_value = None

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.find_by_title("Non Existent Movie")

    assert result is None


@pytest.mark.asyncio
async def test_save_handles_minimal_movie() -> None:
    """Test save handles movie with no optional fields."""
    movie = Movie(
        id=MovieId(value="mov-min"),
        title="Minimal",
        release_date=date(2026, 1, 1),
        directors=("Unknown",),
        cast=(),
    )
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.save.return_value = {
        "id": "mov-min",
        "title": "Minimal",
        "release_date": date(2026, 1, 1),
        "directors": "",
        "cast_members": "",
        "duration_minutes": None,
        "description": None,
    }

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.save(movie)

    assert result.title == "Minimal"
    assert result.directors is None
    assert result.cast is None
    assert result.duration_minutes is None
    assert result.description is None

    mock_gateway.save.assert_awaited_once_with(
        movie_id="mov-min",
        title="Minimal",
        release_date=date(2026, 1, 1),
        directors="Unknown",
        cast="",
        duration_minutes=None,
        description=None,
    )


@pytest.mark.asyncio
async def test_save_handles_none_fields() -> None:
    """Test save when movie has None directors and cast."""
    movie = Movie(
        id=MovieId(value="mov-none"),
        title="No Info",
        release_date=None,
        directors=None,
        cast=None,
    )
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.save.return_value = {
        "id": "mov-none",
        "title": "No Info",
        "release_date": None,
        "directors": None,
        "cast_members": None,
        "duration_minutes": None,
        "description": None,
    }

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.save(movie)

    assert result.title == "No Info"
    assert result.release_date is None
    assert result.directors is None
    assert result.cast is None
    assert result.duration_minutes is None

    mock_gateway.save.assert_awaited_once_with(
        movie_id="mov-none",
        title="No Info",
        release_date=None,
        directors=None,
        cast=None,
        duration_minutes=None,
        description=None,
    )
