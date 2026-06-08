"""Tests for SupabaseScreeningRepository."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import create_autospec

import pytest

from marquise.domain.entities import Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    Price,
    ScreeningId,
    Showtime,
)
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningGateway,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


@pytest.fixture
def sample_screening() -> Screening:
    """Provide a sample Screening for tests."""
    return Screening(
        id=ScreeningId(value="scr-123"),
        movie_id=MovieId(value="mov-456"),
        cinema_id=CinemaId(value="cin-789"),
        showtime=Showtime(value=datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc)),
        price=Price(value=14.99),
    )


@pytest.fixture
def gateway_dict() -> dict:
    """Provide a sample gateway return dict."""
    return {
        "id": "scr-123",
        "movie_id": "mov-456",
        "cinema_id": "cin-789",
        "showtime": "2026-06-07T19:30:00+00:00",
        "price": 14.99,
    }


@pytest.mark.asyncio
async def test_save(sample_screening: Screening) -> None:
    """Test save delegates to gateway and maps result."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.save.return_value = {
        "id": "scr-123",
        "movie_id": "mov-456",
        "cinema_id": "cin-789",
        "showtime": "2026-06-07T19:30:00+00:00",
        "price": 14.99,
        "__inserted": True,
    }

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result, was_inserted = await repo.save(sample_screening)

    assert result.id == ScreeningId(value="scr-123")
    assert result.movie_id == MovieId(value="mov-456")
    assert result.cinema_id == CinemaId(value="cin-789")
    assert result.price == Price(value=14.99)
    mock_gateway.save.assert_awaited_once_with(
        screening_id="scr-123",
        movie_id="mov-456",
        cinema_id="cin-789",
        showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc),
        price=14.99,
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
    assert result.movie_id == MovieId(value="mov-456")
    mock_gateway.find_by_id.assert_awaited_once_with(screening_id="scr-123")


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
    start = datetime(2026, 6, 7, tzinfo=timezone.utc)
    end = datetime(2026, 6, 7, 23, 59, 59, tzinfo=timezone.utc)
    results = await repo.find_by_cinema_and_date_range(
        cinema_id=CinemaId(value="cin-789"),
        start_date=start,
        end_date=end,
    )

    assert len(results) == 1
    assert results[0].id == ScreeningId(value="scr-123")
    mock_gateway.find_by_cinema_and_date_range.assert_awaited_once_with(
        cinema_id="cin-789",
        start_date=start,
        end_date=end,
    )


@pytest.mark.asyncio
async def test_find_by_cinema_and_date_range_empty() -> None:
    """Test find_by_cinema_and_date_range returns empty list."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_by_cinema_and_date_range.return_value = []

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    results = await repo.find_by_cinema_and_date_range(
        cinema_id=CinemaId(value="cin-789"),
        start_date=datetime(2026, 6, 7, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 7, 23, 59, 59, tzinfo=timezone.utc),
    )

    assert results == []
