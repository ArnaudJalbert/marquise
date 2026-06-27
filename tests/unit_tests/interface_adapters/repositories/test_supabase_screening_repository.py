"""Tests for SupabaseScreeningRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)
from marquise.interface_adapters.repositories.protocols.screening import (
    SaveOutcome,
    ScreeningGateway,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide a sample Cinema for tests."""
    return Cinema(
        id=CinemaId(value="cin-789"),
        name="Test Cinema",
    )


@pytest.fixture
def sample_movie() -> Movie:
    """Provide a sample Movie for tests."""
    return Movie(
        id=MovieId(value="mov-456"),
        title="Test Movie",
    )


@pytest.fixture
def sample_screening(sample_cinema: Cinema, sample_movie: Movie) -> Screening:
    """Provide a sample Screening for tests."""
    return Screening(
        id=ScreeningId(value="scr-123"),
        movie=sample_movie,
        cinema=sample_cinema,
        showtime=Showtime(value=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)),
    )


@pytest.fixture
def gateway_dict() -> dict:
    """Provide a sample gateway return dict with joined data.

    The showtime value is a naive datetime to simulate asyncpg's return
    from a ``TIMESTAMP`` column.
    """
    return {
        "id": "scr-123",
        "movie_id": "mov-456",
        "cinema_id": "cin-789",
        "showtime": datetime(2026, 6, 7, 19, 30, 0),
        "external_id": None,
        "ticket_url": None,
        "room": None,
        "language": None,
        "movie__id": "mov-456",
        "movie__title": "Test Movie",
        "movie__release_year": None,
        "movie__directors": None,
        "movie__cast_members": None,
        "movie__duration_minutes": None,
        "movie__description": None,
        "movie__poster_url": None,
        "movie__trailer_url": None,
        "movie__genres": None,
        "movie__original_title": None,
        "movie__rating": None,
        "movie__origin_countries": None,
        "cinema__id": "cin-789",
        "cinema__name": "Test Cinema",
        "cinema__address": None,
        "cinema__city": None,
        "cinema__website": None,
    }


@pytest.mark.asyncio
async def test_save(
    sample_screening: Screening,
    sample_cinema: Cinema,
    sample_movie: Movie,
) -> None:
    """Test save delegates to gateway and maps result."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.save.return_value = SaveOutcome(
        row={
            "id": "scr-123",
            "movie_id": "mov-456",
            "cinema_id": "cin-789",
            "showtime": datetime(2026, 6, 7, 19, 30, 0),
            "external_id": None,
            "ticket_url": None,
            "room": None,
            "language": None,
        },
        inserted=True,
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result, was_inserted = await repo.save(sample_screening)

    assert result.id == ScreeningId(value="scr-123")
    assert result.movie == sample_movie
    assert result.cinema == sample_cinema
    assert result.showtime.value.tzinfo == UTC
    assert result.showtime.value == datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    assert result.external_id is None
    assert result.ticket_url is None
    assert result.room is None
    assert result.language is None
    mock_gateway.save.assert_awaited_once_with(
        screening_id="scr-123",
        movie_id="mov-456",
        cinema_id="cin-789",
        showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        external_id=None,
        ticket_url=None,
        room=None,
        language=None,
    )


@pytest.mark.asyncio
async def test_find_by_id(gateway_dict: dict) -> None:
    """Test find_by_id returns entity when found."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_by_id.return_value = gateway_dict

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.find_by_id(ScreeningId(value="scr-123"))

    assert result is not None
    assert result.id == ScreeningId(value="scr-123")
    assert result.movie.id == MovieId(value="mov-456")
    assert result.showtime.value.tzinfo == UTC
    assert result.showtime.value == datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    mock_gateway.find_by_id.assert_awaited_once_with(screening_id="scr-123")


@pytest.mark.asyncio
async def test_save_with_timezone_aware_datetime(
    sample_screening: Screening,
) -> None:
    """Test save handles gateway returning timezone-aware datetime."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.save.return_value = SaveOutcome(
        row={
            "id": "scr-123",
            "movie_id": "mov-456",
            "cinema_id": "cin-789",
            "showtime": datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            "external_id": None,
            "ticket_url": None,
            "room": None,
            "language": None,
        },
        inserted=True,
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result, was_inserted = await repo.save(sample_screening)

    assert result.showtime.value.tzinfo == UTC
    assert was_inserted


@pytest.mark.asyncio
async def test_save_with_iso_string_showtime(
    sample_screening: Screening,
) -> None:
    """Test save handles gateway returning an ISO string without tz info."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.save.return_value = SaveOutcome(
        row={
            "id": "scr-123",
            "movie_id": "mov-456",
            "cinema_id": "cin-789",
            "showtime": "2026-06-07T19:30:00",
            "external_id": None,
            "ticket_url": None,
            "room": None,
            "language": None,
        },
        inserted=True,
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result, was_inserted = await repo.save(sample_screening)

    assert result.showtime.value.tzinfo == UTC
    assert result.showtime.value == datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    assert was_inserted


@pytest.mark.asyncio
async def test_find_by_id_missing() -> None:
    """Test find_by_id returns None when not found."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_by_id.return_value = None

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.find_by_id(ScreeningId(value="scr-999"))

    assert result is None


@pytest.mark.asyncio
async def test_find_by_cinema_and_date_range(gateway_dict: dict) -> None:
    """Test find_by_cinema_and_date_range returns list of entities."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_by_cinema_and_date_range.return_value = [gateway_dict]

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    start = datetime(2026, 6, 7, tzinfo=UTC)
    end = datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC)
    results = await repo.find_by_cinema_and_date_range(
        cinema_id=CinemaId(value="cin-789"),
        start_date=start,
        end_date=end,
    )

    assert len(results) == 1
    assert results[0].id == ScreeningId(value="scr-123")
    assert results[0].showtime.value.tzinfo == UTC
    assert results[0].showtime.value == datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    mock_gateway.find_by_cinema_and_date_range.assert_awaited_once_with(
        cinema_id="cin-789",
        start_date=start,
        end_date=end,
    )


@pytest.mark.asyncio
async def test_to_entity_populates_release_year() -> None:
    """Test _to_entity populates release_year from gateway data."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    raw = {
        "id": "scr-456",
        "movie_id": "mov-456",
        "cinema_id": "cin-789",
        "showtime": datetime(2026, 7, 1, 14, 0, 0),
        "external_id": None,
        "ticket_url": None,
        "room": None,
        "language": None,
        "movie__id": "mov-456",
        "movie__title": "Test Movie",
        "movie__release_year": 2026,
        "movie__directors": None,
        "movie__cast_members": None,
        "movie__duration_minutes": None,
        "movie__description": None,
        "movie__poster_url": None,
        "movie__trailer_url": None,
        "movie__genres": None,
        "movie__original_title": None,
        "movie__rating": None,
        "movie__origin_countries": None,
        "cinema__id": "cin-789",
        "cinema__name": "Test Cinema",
        "cinema__address": None,
        "cinema__city": None,
        "cinema__website": None,
    }
    mock_gateway.find_by_id.return_value = raw

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.find_by_id(ScreeningId(value="scr-456"))

    assert result is not None
    assert result.movie.release_year == 2026


@pytest.mark.asyncio
async def test_find_by_cinema_and_date_range_empty() -> None:
    """Test find_by_cinema_and_date_range returns empty list."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_by_cinema_and_date_range.return_value = []

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    results = await repo.find_by_cinema_and_date_range(
        cinema_id=CinemaId(value="cin-789"),
        start_date=datetime(2026, 6, 7, tzinfo=UTC),
        end_date=datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC),
    )

    assert results == []
