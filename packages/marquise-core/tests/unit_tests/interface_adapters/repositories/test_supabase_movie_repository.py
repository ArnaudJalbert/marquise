"""Tests for SupabaseMovieRepository."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from marquise.interface_adapters.repositories.protocols.base import GatewayPage
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
        release_year=2010,
        directors=("Christopher Nolan",),
        cast=("Leonardo DiCaprio", "Joseph Gordon-Levitt"),
        duration_minutes=148,
        description="A thief who steals corporate secrets...",
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres=("Sci-Fi", "Action"),
        original_title="Inception",
        rating="PG-13",
        origin_countries=("United States", "United Kingdom"),
    )


@pytest.fixture
def gateway_dict() -> dict:
    """Provide a sample gateway return dict."""
    return {
        "id": "mov-123",
        "title": "Inception",
        "release_year": 2010,
        "directors": "Christopher Nolan",
        "cast_members": "Leonardo DiCaprio,Joseph Gordon-Levitt",
        "duration_minutes": 148,
        "description": "A thief who steals corporate secrets...",
        "poster_url": "https://example.com/poster.jpg",
        "trailer_url": "https://example.com/trailer",
        "genres": "Sci-Fi,Action",
        "original_title": "Inception",
        "rating": "PG-13",
        "origin_countries": "United States,United Kingdom",
    }


@pytest.mark.asyncio
async def test_save(sample_movie: Movie) -> None:
    """Test save delegates to gateway and maps result."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.save.return_value = {
        "id": "mov-123",
        "title": "Inception",
        "release_year": 2010,
        "directors": "Christopher Nolan",
        "cast_members": "Leonardo DiCaprio,Joseph Gordon-Levitt",
        "duration_minutes": 148,
        "description": "A thief who steals corporate secrets...",
        "poster_url": "https://example.com/poster.jpg",
        "trailer_url": "https://example.com/trailer",
        "genres": "Sci-Fi,Action",
        "original_title": "Inception",
        "rating": "PG-13",
        "origin_countries": "United States,United Kingdom",
    }

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.save(sample_movie)

    assert result.id == MovieId(value="mov-123")
    assert result.title == "Inception"
    assert result.directors == ("Christopher Nolan",)
    assert result.cast == ("Leonardo DiCaprio", "Joseph Gordon-Levitt")
    assert result.duration_minutes == 148
    assert result.poster_url == "https://example.com/poster.jpg"
    assert result.genres == ("Sci-Fi", "Action")
    mock_gateway.save.assert_awaited_once_with(
        movie_id="mov-123",
        title="Inception",
        release_year=2010,
        directors="Christopher Nolan",
        cast="Leonardo DiCaprio,Joseph Gordon-Levitt",
        duration_minutes=148,
        description="A thief who steals corporate secrets...",
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres="Sci-Fi,Action",
        original_title="Inception",
        rating="PG-13",
        origin_countries="United States,United Kingdom",
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
async def test_find_by_ids(gateway_dict: dict) -> None:
    """Test find_by_ids maps gateway rows to entities and passes plain ids."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_by_ids.return_value = [gateway_dict]

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.find_by_ids(
        [MovieId(value="mov-123"), MovieId(value="mov-999")]
    )

    assert len(result) == 1
    assert result[0].id == MovieId(value="mov-123")
    mock_gateway.find_by_ids.assert_awaited_once_with(movie_ids=["mov-123", "mov-999"])


@pytest.mark.asyncio
async def test_find_by_ids_omits_missing(gateway_dict: dict) -> None:
    """Test find_by_ids returns an empty list when no ids match."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_by_ids.return_value = []

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.find_by_ids([MovieId(value="missing")])

    assert result == []


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
        directors=("Unknown",),
        cast=None,
    )
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.save.return_value = {
        "id": "mov-min",
        "title": "Minimal",
        "release_year": None,
        "directors": "",
        "cast_members": None,
        "duration_minutes": None,
        "description": None,
        "poster_url": None,
        "trailer_url": None,
        "genres": None,
        "original_title": None,
        "rating": None,
        "origin_countries": None,
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
        release_year=None,
        directors="Unknown",
        cast=None,
        duration_minutes=None,
        description=None,
        poster_url=None,
        trailer_url=None,
        genres=None,
        original_title=None,
        rating=None,
        origin_countries=None,
    )


@pytest.mark.asyncio
async def test_save_handles_none_fields() -> None:
    """Test save when movie has None directors and cast."""
    movie = Movie(
        id=MovieId(value="mov-none"),
        title="No Info",
        directors=None,
        cast=None,
    )
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.save.return_value = {
        "id": "mov-none",
        "title": "No Info",
        "release_year": None,
        "directors": None,
        "cast_members": None,
        "duration_minutes": None,
        "description": None,
        "poster_url": None,
        "trailer_url": None,
        "genres": None,
        "original_title": None,
        "rating": None,
        "origin_countries": None,
    }

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.save(movie)

    assert result.title == "No Info"
    assert result.release_year is None
    assert result.directors is None
    assert result.cast is None
    assert result.duration_minutes is None

    mock_gateway.save.assert_awaited_once_with(
        movie_id="mov-none",
        title="No Info",
        release_year=None,
        directors=None,
        cast=None,
        duration_minutes=None,
        description=None,
        poster_url=None,
        trailer_url=None,
        genres=None,
        original_title=None,
        rating=None,
        origin_countries=None,
    )


@pytest.mark.asyncio
async def test_exists_by_id() -> None:
    """Verify exists_by_id returns True when the gateway returns True."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.exists_by_id.return_value = True

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.exists_by_id(MovieId(value="mov-123"))

    assert result is True
    mock_gateway.exists_by_id.assert_awaited_once_with(movie_id="mov-123")


@pytest.mark.asyncio
async def test_exists_by_id_missing() -> None:
    """Verify exists_by_id returns False when the gateway returns False."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.exists_by_id.return_value = False

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.exists_by_id(MovieId(value="mov-999"))

    assert result is False


@pytest.mark.asyncio
async def test_find_all_without_filter(gateway_dict: dict) -> None:
    """Verify find_all without filter returns all mapped movies."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_all.return_value = GatewayPage(rows=[gateway_dict], total=1)

    repo = SupabaseMovieRepository(gateway=mock_gateway)
    result = await repo.find_all()

    assert len(result.items) == 1
    assert result.items[0].title == "Inception"
    assert result.total == 1
    mock_gateway.find_all.assert_awaited_once_with(
        title_filter=None, limit=None, offset=0
    )


@pytest.mark.asyncio
async def test_find_all_with_filter(gateway_dict: dict) -> None:
    """Verify find_all with filter delegates the filter to the gateway."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_all.return_value = GatewayPage(rows=[gateway_dict], total=1)

    result = await SupabaseMovieRepository(gateway=mock_gateway).find_all(
        title_filter="Incep"
    )

    assert len(result.items) == 1
    assert result.items[0].title == "Inception"
    mock_gateway.find_all.assert_awaited_once_with(
        title_filter="Incep", limit=None, offset=0
    )


@pytest.mark.asyncio
async def test_find_all_with_pagination(gateway_dict: dict) -> None:
    """Verify find_all forwards limit/offset and surfaces the gateway's total."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_all.return_value = GatewayPage(rows=[gateway_dict], total=50)

    result = await SupabaseMovieRepository(gateway=mock_gateway).find_all(
        limit=1, offset=5
    )

    assert len(result.items) == 1
    assert result.total == 50
    mock_gateway.find_all.assert_awaited_once_with(title_filter=None, limit=1, offset=5)


@pytest.mark.asyncio
async def test_find_all_returns_empty_page() -> None:
    """Verify find_all returns an empty page when no rows match."""
    mock_gateway = create_autospec(MovieGateway, instance=True)
    mock_gateway.find_all.return_value = GatewayPage(rows=[], total=0)

    result = await SupabaseMovieRepository(gateway=mock_gateway).find_all(
        title_filter="Nonexistent"
    )

    assert result.items == []
    assert result.total == 0
