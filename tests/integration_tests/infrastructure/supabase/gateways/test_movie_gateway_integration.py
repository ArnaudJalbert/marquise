"""Integration tests for SupabaseMovieGateway."""

from __future__ import annotations

import pytest

from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway


@pytest.mark.asyncio
async def test_save_and_find_by_id(movie_gateway: SupabaseMovieGateway) -> None:
    """Verify a movie can be saved and then retrieved by ID."""
    result = await movie_gateway.save(
        movie_id="mov-001",
        title="Inception",
        release_year=2010,
        directors="Christopher Nolan",
        cast="Leonardo DiCaprio,Joseph Gordon-Levitt",
        duration_minutes=148,
        description="A thief who steals corporate secrets through dream sharing.",
    )
    assert result["id"] == "mov-001"
    assert result["title"] == "Inception"
    assert result["release_year"] == 2010
    assert result["directors"] == "Christopher Nolan"
    assert result["duration_minutes"] == 148

    found = await movie_gateway.find_by_id("mov-001")
    assert found is not None
    assert found["title"] == "Inception"
    assert found["cast_members"] == "Leonardo DiCaprio,Joseph Gordon-Levitt"


@pytest.mark.asyncio
async def test_find_by_id_missing(movie_gateway: SupabaseMovieGateway) -> None:
    """Verify find_by_id returns None for a non-existent ID."""
    found = await movie_gateway.find_by_id("mov-missing")
    assert found is None


@pytest.mark.asyncio
async def test_find_by_title(movie_gateway: SupabaseMovieGateway) -> None:
    """Verify a movie can be found by its title."""
    await movie_gateway.save(
        movie_id="mov-002",
        title="The Matrix",
        release_year=1999,
        directors="The Wachowskis",
        cast="Keanu Reeves,Laurence Fishburne",
    )

    found = await movie_gateway.find_by_title("The Matrix")
    assert found is not None
    assert found["id"] == "mov-002"
    assert found["release_year"] == 1999


@pytest.mark.asyncio
async def test_find_by_title_missing(movie_gateway: SupabaseMovieGateway) -> None:
    """Verify find_by_title returns None for a non-existent title."""
    found = await movie_gateway.find_by_title("Non Existent Movie")
    assert found is None


@pytest.mark.asyncio
async def test_save_updates_existing_on_title_conflict(
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify save upserts when a movie with the same title exists."""
    await movie_gateway.save(
        movie_id="mov-003",
        title="Duplicate Title",
        release_year=2020,
        directors="Original Director",
        cast="Actor A",
    )

    saved = await movie_gateway.save(
        movie_id="mov-004",
        title="Duplicate Title",
        release_year=2021,
        directors="Updated Director",
        cast="Actor B",
    )
    assert saved["title"] == "Duplicate Title"
    assert saved["directors"] == "Updated Director"
    assert saved["release_year"] == 2021


@pytest.mark.asyncio
async def test_save_handles_minimal_fields(
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify a movie can be saved with only required fields."""
    result = await movie_gateway.save(
        movie_id="mov-005",
        title="Minimal Movie",
        release_year=2026,
        directors="",
        cast="",
    )
    assert result["id"] == "mov-005"
    assert result["title"] == "Minimal Movie"
    assert result["duration_minutes"] is None
    assert result["description"] is None
    assert result["directors"] == ""


@pytest.mark.asyncio
async def test_save_handles_none_fields(
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify a movie can be saved with None for optional fields."""
    result = await movie_gateway.save(
        movie_id="mov-006",
        title="None Fields Movie",
        release_year=None,
        directors=None,
        cast=None,
    )
    assert result["id"] == "mov-006"
    assert result["title"] == "None Fields Movie"
    assert result["release_year"] is None
    assert result["directors"] is None
    assert result["cast_members"] is None


@pytest.mark.asyncio
async def test_save_does_not_overwrite_with_none_on_conflict(
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify upsert does not overwrite known values with None."""
    await movie_gateway.save(
        movie_id="mov-007",
        title="Preserve Me",
        release_year=2020,
        directors="Known Director",
        cast="Known Cast",
    )

    result = await movie_gateway.save(
        movie_id="mov-008",
        title="Preserve Me",
        release_year=None,
        directors=None,
        cast=None,
    )
    assert result["title"] == "Preserve Me"
    assert result["release_year"] == 2020
    assert result["directors"] == "Known Director"
    assert result["cast_members"] == "Known Cast"
