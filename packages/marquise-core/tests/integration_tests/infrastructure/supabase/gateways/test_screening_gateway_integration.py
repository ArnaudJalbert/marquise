"""Integration tests for SupabaseScreeningGateway."""

from __future__ import annotations

from datetime import UTC, datetime

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
from marquise.interface_adapters.repositories.protocols.base import GatewayError


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
    await movie_gateway.save(movie_id="mov-001", title="Movie A", release_year=None)
    await movie_gateway.save(movie_id="mov-002", title="Movie B", release_year=None)
    await movie_gateway.save(movie_id="mov-003", title="Movie C", release_year=None)


@pytest.mark.asyncio
async def test_save_and_find_by_id(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify a screening can be saved and then retrieved by ID."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    result = await screening_gateway.save(
        screening_id="scr-001",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=showtime,
    )
    assert result.inserted is True
    assert result.row["id"] == "scr-001"
    assert result.row["movie_id"] == "mov-001"
    assert result.row["cinema_id"] == "cin-001"

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
async def test_search_by_cinema_and_date_range(
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
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-004",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 20, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-005",
        movie_id="mov-003",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 10, 21, 0, 0, tzinfo=UTC),
    )

    page = await screening_gateway.search(
        cinema_id="cin-003",
        start_date=datetime(2026, 6, 7, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 8, 23, 59, 59, tzinfo=UTC),
    )
    assert page.total == 2
    assert len(page.rows) == 2
    assert page.rows[0]["id"] == "scr-003"
    assert page.rows[1]["id"] == "scr-004"


@pytest.mark.asyncio
async def test_search_by_cinema_and_date_range_empty(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify search returns an empty page when no match."""
    page = await screening_gateway.search(
        cinema_id="cin-empty",
        start_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC),
    )
    assert page.rows == []
    assert page.total == 0


@pytest.mark.asyncio
async def test_search_by_cinema_and_date_range_with_limit_and_offset(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify limit/offset return the correct slice while total reflects all rows."""
    await _seed_parents(gateway, movie_gateway)
    for i, day in enumerate((7, 8, 10)):
        await screening_gateway.save(
            screening_id=f"scr-page-{i}",
            movie_id="mov-001",
            cinema_id="cin-003",
            showtime=datetime(2026, 6, day, 19, 0, 0, tzinfo=UTC),
        )

    page = await screening_gateway.search(
        cinema_id="cin-003",
        start_date=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC),
        limit=2,
        offset=1,
    )

    assert page.total == 3
    assert [row["id"] for row in page.rows] == ["scr-page-1", "scr-page-2"]


@pytest.mark.asyncio
async def test_search_by_cinema_and_date_range_offset_past_total(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """An offset beyond the result set returns no rows but the true total.

    Exercises the fallback COUNT(*) path: when LIMIT/OFFSET returns zero
    rows, there is no row to read a windowed total off, so the gateway must
    fall back to a separate count query.
    """
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-past-0",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
    )

    page = await screening_gateway.search(
        cinema_id="cin-003",
        start_date=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC),
        limit=10,
        offset=100,
    )

    assert page.rows == []
    assert page.total == 1


@pytest.mark.asyncio
async def test_save_upserts_on_unique_key_conflict(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify save returns the existing row on conflict."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 9, 19, 30, 0, tzinfo=UTC)
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
    assert saved.row["id"] == "scr-006"
    assert saved.inserted is False

    new_id = await screening_gateway.find_by_id("scr-007")
    assert new_id is None


@pytest.mark.asyncio
async def test_save_raises_gateway_error_on_external_id_conflict(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify save raises GatewayError when external_id collides across rows.

    Reproduces the Cineplex bug: an external_id reused for a different
    (cinema_id, movie_id, showtime) can't be resolved by the composite-key
    ON CONFLICT clause and must surface as a GatewayError instead of a raw
    asyncpg.UniqueViolationError.
    """
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-008",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=datetime(2026, 6, 11, 19, 30, 0, tzinfo=UTC),
        external_id="ext-conflict",
    )

    with pytest.raises(GatewayError, match="ext-conflict"):
        await screening_gateway.save(
            screening_id="scr-009",
            movie_id="mov-002",
            cinema_id="cin-004",
            showtime=datetime(2026, 6, 12, 21, 0, 0, tzinfo=UTC),
            external_id="ext-conflict",
        )


@pytest.mark.asyncio
async def test_search_by_movie_id(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify search filters by exact movie_id."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-search-001",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-search-002",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 20, 0, 0, tzinfo=UTC),
    )

    page = await screening_gateway.search(movie_id="mov-001")

    assert page.total == 1
    assert page.rows[0]["id"] == "scr-search-001"


@pytest.mark.asyncio
async def test_search_by_movie_title(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify search filters by a case-insensitive movie title substring."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-search-003",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
    )

    page = await screening_gateway.search(movie_title="movie a")

    assert page.total == 1
    assert page.rows[0]["id"] == "scr-search-003"


@pytest.mark.asyncio
async def test_search_by_cinema_id_and_date_range(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify search filters by cinema_id combined with a date range."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-search-004",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-search-005",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 10, 21, 0, 0, tzinfo=UTC),
    )

    page = await screening_gateway.search(
        cinema_id="cin-003",
        start_date=datetime(2026, 6, 7, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 8, 23, 59, 59, tzinfo=UTC),
    )

    assert page.total == 1
    assert page.rows[0]["id"] == "scr-search-004"


@pytest.mark.asyncio
async def test_search_by_language(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify search filters by exact language."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-search-006",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
        language="V.O.",
    )
    await screening_gateway.save(
        screening_id="scr-search-007",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 20, 0, 0, tzinfo=UTC),
        language="V.F.",
    )

    page = await screening_gateway.search(language="V.O.")

    assert page.total == 1
    assert page.rows[0]["id"] == "scr-search-006"


@pytest.mark.asyncio
async def test_search_with_no_filters_returns_all(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify search with no filters returns every screening, paginated."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-search-008",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-search-009",
        movie_id="mov-002",
        cinema_id="cin-004",
        showtime=datetime(2026, 6, 8, 20, 0, 0, tzinfo=UTC),
    )

    page = await screening_gateway.search(limit=1, offset=0)

    assert page.total >= 2
    assert len(page.rows) == 1


@pytest.mark.asyncio
async def test_search_empty(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify search returns an empty page when no screening matches."""
    page = await screening_gateway.search(movie_title="nonexistent-movie-xyz")

    assert page.rows == []
    assert page.total == 0


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify distinct movies are returned for a cinema within a date range."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-distinct-001",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-distinct-002",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 20, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-distinct-003",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC),
    )

    page = await screening_gateway.find_distinct_movies_by_cinema(
        cinema_id="cin-003",
        start_date=datetime(2026, 6, 7, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 8, 23, 59, 59, tzinfo=UTC),
    )

    assert page.total == 2
    assert {row["id"] for row in page.rows} == {"mov-001", "mov-002"}


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema_empty(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify an empty page is returned when no screening matches."""
    page = await screening_gateway.find_distinct_movies_by_cinema(
        cinema_id="cin-empty",
        start_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC),
    )
    assert page.rows == []
    assert page.total == 0


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema_with_limit_and_offset(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify limit/offset paginate distinct movies while total reflects all of them."""
    await _seed_parents(gateway, movie_gateway)
    for movie_id in ("mov-001", "mov-002", "mov-003"):
        await screening_gateway.save(
            screening_id=f"scr-distinct-page-{movie_id}",
            movie_id=movie_id,
            cinema_id="cin-004",
            showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
        )

    page = await screening_gateway.find_distinct_movies_by_cinema(
        cinema_id="cin-004",
        start_date=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC),
        limit=2,
        offset=1,
    )

    assert page.total == 3
    assert len(page.rows) == 2


@pytest.mark.asyncio
async def test_replace_updates_all_fields_by_id(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify replace writes identity and optional fields for a known ID."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-replace-001",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        ticket_url="https://old.example/t",
        room="Salle 1",
        language="V.F.",
    )

    replaced = await screening_gateway.replace(
        screening_id="scr-replace-001",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 21, 0, 0, tzinfo=UTC),
        ticket_url=None,
        room="Salle 9",
        language="V.O.",
    )

    assert replaced is not None
    assert replaced["id"] == "scr-replace-001"
    assert replaced["movie_id"] == "mov-002"
    assert replaced["cinema_id"] == "cin-003"
    assert replaced["ticket_url"] is None
    assert replaced["room"] == "Salle 9"
    assert replaced["language"] == "V.O."

    found = await screening_gateway.find_by_id("scr-replace-001")
    assert found is not None
    assert found["movie__id"] == "mov-002"
    assert found["cinema__id"] == "cin-003"


@pytest.mark.asyncio
async def test_replace_missing_returns_none(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify replace returns None when the screening ID does not exist."""
    result = await screening_gateway.replace(
        screening_id="scr-replace-missing",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 8, 21, 0, 0, tzinfo=UTC),
    )
    assert result is None


@pytest.mark.asyncio
async def test_replace_raises_on_identity_conflict(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify replace raises GatewayError when identity collides."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 9, 19, 0, 0, tzinfo=UTC)
    await screening_gateway.save(
        screening_id="scr-replace-conflict-a",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=showtime,
    )
    await screening_gateway.save(
        screening_id="scr-replace-conflict-b",
        movie_id="mov-002",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 10, 19, 0, 0, tzinfo=UTC),
    )

    with pytest.raises(GatewayError):
        await screening_gateway.replace(
            screening_id="scr-replace-conflict-b",
            movie_id="mov-001",
            cinema_id="cin-001",
            showtime=showtime,
        )


@pytest.mark.asyncio
async def test_delete_removes_row(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify delete removes the screening and returns None."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-delete-001",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
    )

    deleted = await screening_gateway.delete("scr-delete-001")
    assert deleted is None
    assert await screening_gateway.find_by_id("scr-delete-001") is None


@pytest.mark.asyncio
async def test_delete_missing_raises_gateway_error(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify delete raises GatewayError when screening ID does not exist."""
    with pytest.raises(GatewayError, match="scr-delete-missing"):
        await screening_gateway.delete("scr-delete-missing")


@pytest.mark.asyncio
async def test_delete_if_orphan_removes_unreferenced_movie(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Orphan cleanup deletes movie with no remaining screenings."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-orphan-001",
        movie_id="mov-003",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
    )
    await screening_gateway.delete("scr-orphan-001")

    await movie_gateway.delete_if_orphan("mov-003")

    assert await movie_gateway.find_by_id("mov-003") is None


@pytest.mark.asyncio
async def test_delete_if_orphan_keeps_shared_movie(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Orphan cleanup keeps movie still referenced by another screening."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-orphan-002",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-orphan-003",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 19, 30, 0, tzinfo=UTC),
    )
    await screening_gateway.delete("scr-orphan-002")

    await movie_gateway.delete_if_orphan("mov-001")

    assert await movie_gateway.find_by_id("mov-001") is not None
