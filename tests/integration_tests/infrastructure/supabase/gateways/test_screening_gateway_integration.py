"""Integration tests for SupabaseScreeningGateway."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from marquise.infrastructure.supabase.gateways.cinema import (
    SupabaseCinemaGateway,
)
from marquise.infrastructure.supabase.gateways.movie import (
    SupabaseMovieGateway,
)
from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)


async def _seed_parents(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Create parent rows needed for FK constraints."""
    await gateway.save(cinema_id="cin-001", name="Cinema One", address=None, city=None)
    await gateway.save(
        cinema_id="cin-003", name="Cinema Three", address=None, city=None
    )
    await gateway.save(cinema_id="cin-004", name="Cinema Four", address=None, city=None)
    await movie_gateway.save(movie_id="mov-001", title="Movie A", release_date=None)
    await movie_gateway.save(movie_id="mov-002", title="Movie B", release_date=None)
    await movie_gateway.save(movie_id="mov-003", title="Movie C", release_date=None)


@pytest.mark.asyncio
async def test_save_and_find_by_id(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify a screening can be saved and then retrieved by ID."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc)
    result = await screening_gateway.save(
        screening_id="scr-001",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=showtime,
    )
    assert result["id"] == "scr-001"
    assert result["movie_id"] == "mov-001"
    assert result["cinema_id"] == "cin-001"

    found = await screening_gateway.find_by_id("scr-001")
    assert found is not None
    assert found["movie__id"] == "mov-001"
    assert found["cinema__id"] == "cin-001"


@pytest.mark.asyncio
async def test_find_by_id_missing(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify find_by_id returns None for a non-existent ID."""
    found = await screening_gateway.find_by_id("scr-missing")
    assert found is None


@pytest.mark.asyncio
async def test_find_by_cinema_and_date_range(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify screenings can be found within a date range for a cinema."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-003",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=timezone.utc),
    )
    await screening_gateway.save(
        screening_id="scr-004",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 20, 0, 0, tzinfo=timezone.utc),
    )
    await screening_gateway.save(
        screening_id="scr-005",
        movie_id="mov-003",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 10, 21, 0, 0, tzinfo=timezone.utc),
    )

    found = await screening_gateway.find_by_cinema_and_date_range(
        cinema_id="cin-003",
        start_date=datetime(2026, 6, 7, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 8, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert len(found) == 2
    assert found[0]["id"] == "scr-003"
    assert found[1]["id"] == "scr-004"


@pytest.mark.asyncio
async def test_find_by_cinema_and_date_range_empty(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify find_by_cinema_and_date_range returns empty list when no match."""
    found = await screening_gateway.find_by_cinema_and_date_range(
        cinema_id="cin-empty",
        start_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert found == []


@pytest.mark.asyncio
async def test_save_upserts_on_unique_key_conflict(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify save returns the existing row on conflict."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 9, 19, 30, 0, tzinfo=timezone.utc)
    await screening_gateway.save(
        screening_id="scr-006",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=showtime,
    )

    saved = await screening_gateway.save(
        screening_id="scr-007",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=showtime,
    )
    assert saved["id"] == "scr-006"
    assert saved.get("__inserted") is False

    new_id = await screening_gateway.find_by_id("scr-007")
    assert new_id is None
