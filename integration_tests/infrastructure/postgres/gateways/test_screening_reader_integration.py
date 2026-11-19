"""Integration tests for PostgresScreeningReadGateway search SQL."""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg
import pytest

from marquise.infrastructure.postgres.gateways.cinema import PostgresCinemaGateway
from marquise.infrastructure.postgres.gateways.movie import PostgresMovieGateway
from marquise.infrastructure.postgres.gateways.screening import (
    PostgresScreeningGateway,
)
from marquise.infrastructure.postgres.gateways.screening_reader import (
    PostgresScreeningReadGateway,
)


@pytest.fixture
def reader(db_pool: asyncpg.Pool) -> PostgresScreeningReadGateway:
    """Provide the screening reader over the test schema."""
    return PostgresScreeningReadGateway(db_pool, "marquise-test")


async def _seed_parents(
    gateway: PostgresCinemaGateway,
    movie_gateway: PostgresMovieGateway,
) -> None:
    """Create one cinema and two movies for FK constraints."""
    await gateway.save(cinema_id="cin-001", name="Cinema One", address=None, city=None)
    await movie_gateway.save(movie_id="mov-001", title="Dune", release_year=None)
    await movie_gateway.save(movie_id="mov-002", title="Other Film", release_year=None)


@pytest.mark.asyncio
async def test_search_filters_by_title_case_insensitively(
    reader: PostgresScreeningReadGateway,
    screening_gateway: PostgresScreeningGateway,
    gateway: PostgresCinemaGateway,
    movie_gateway: PostgresMovieGateway,
) -> None:
    """A title filter matches a substring regardless of case."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 7, 19, 0, tzinfo=UTC)
    await screening_gateway.save(
        screening_id="scr-dune",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=showtime,
    )
    await screening_gateway.save(
        screening_id="scr-other",
        movie_id="mov-002",
        cinema_id="cin-001",
        showtime=showtime,
    )

    page = await reader.search(movie_title="DUN")

    assert page.total == 1
    assert [row["id"] for row in page.rows] == ["scr-dune"]


@pytest.mark.asyncio
async def test_search_filters_by_language(
    reader: PostgresScreeningReadGateway,
    screening_gateway: PostgresScreeningGateway,
    gateway: PostgresCinemaGateway,
    movie_gateway: PostgresMovieGateway,
) -> None:
    """A language filter returns only screenings in that language."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-vo",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 19, 0, tzinfo=UTC),
        language="V.O.",
    )
    await screening_gateway.save(
        screening_id="scr-vf",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 21, 0, tzinfo=UTC),
        language="V.F.",
    )

    page = await reader.search(language="V.O.")

    assert page.total == 1
    assert [row["id"] for row in page.rows] == ["scr-vo"]


@pytest.mark.asyncio
async def test_search_filters_by_movie_id_and_cinema_id(
    reader: PostgresScreeningReadGateway,
    screening_gateway: PostgresScreeningGateway,
    gateway: PostgresCinemaGateway,
    movie_gateway: PostgresMovieGateway,
) -> None:
    """Movie and cinema ID filters return only screenings that match them."""
    await _seed_parents(gateway, movie_gateway)
    await gateway.save(cinema_id="cin-002", name="Cinema Two", address=None, city=None)
    showtime = datetime(2026, 6, 7, 19, 0, tzinfo=UTC)
    await screening_gateway.save(
        screening_id="scr-dune-one",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=showtime,
    )
    await screening_gateway.save(
        screening_id="scr-other-one",
        movie_id="mov-002",
        cinema_id="cin-001",
        showtime=showtime,
    )
    await screening_gateway.save(
        screening_id="scr-dune-two",
        movie_id="mov-001",
        cinema_id="cin-002",
        showtime=showtime,
    )

    by_movie = await reader.search(movie_id="mov-001")
    by_cinema = await reader.search(cinema_id="cin-002")

    assert sorted(row["id"] for row in by_movie.rows) == [
        "scr-dune-one",
        "scr-dune-two",
    ]
    assert [row["id"] for row in by_cinema.rows] == ["scr-dune-two"]


@pytest.mark.asyncio
async def test_search_date_bounds_are_inclusive(
    reader: PostgresScreeningReadGateway,
    screening_gateway: PostgresScreeningGateway,
    gateway: PostgresCinemaGateway,
    movie_gateway: PostgresMovieGateway,
) -> None:
    """Showtimes at start_date and end_date match; one microsecond past end does not."""
    await _seed_parents(gateway, movie_gateway)
    for screening_id, showtime in (
        ("before", datetime(2026, 6, 7, 18, 59, 59, tzinfo=UTC)),
        ("at-start", datetime(2026, 6, 7, 19, 0, tzinfo=UTC)),
        ("at-end", datetime(2026, 6, 8, 19, 0, tzinfo=UTC)),
        ("after-end", datetime(2026, 6, 8, 19, 0, 0, 1, tzinfo=UTC)),
    ):
        await screening_gateway.save(
            screening_id=screening_id,
            movie_id="mov-001",
            cinema_id="cin-001",
            showtime=showtime,
        )

    page = await reader.search(
        start_date=datetime(2026, 6, 7, 19, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 8, 19, 0, tzinfo=UTC),
    )

    assert page.total == 2
    assert [row["id"] for row in page.rows] == ["at-start", "at-end"]


@pytest.mark.asyncio
async def test_search_total_counts_all_matches_beyond_the_page(
    reader: PostgresScreeningReadGateway,
    screening_gateway: PostgresScreeningGateway,
    gateway: PostgresCinemaGateway,
    movie_gateway: PostgresMovieGateway,
) -> None:
    """Limit and offset return the requested slice while total covers all matches."""
    await _seed_parents(gateway, movie_gateway)
    for i, day in enumerate((7, 8, 10)):
        await screening_gateway.save(
            screening_id=f"scr-page-{i}",
            movie_id="mov-001",
            cinema_id="cin-001",
            showtime=datetime(2026, 6, day, 19, 0, tzinfo=UTC),
        )

    page = await reader.search(limit=2, offset=1)

    assert page.total == 3
    assert [row["id"] for row in page.rows] == ["scr-page-1", "scr-page-2"]


@pytest.mark.asyncio
async def test_search_offset_past_total_returns_no_rows_and_true_total(
    reader: PostgresScreeningReadGateway,
    screening_gateway: PostgresScreeningGateway,
    gateway: PostgresCinemaGateway,
    movie_gateway: PostgresMovieGateway,
) -> None:
    """An offset beyond the result set returns no rows but the true total.

    When LIMIT/OFFSET returns zero rows there is no windowed total to read,
    so the reader falls back to a separate COUNT(*) query.
    """
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-past-0",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 19, 0, tzinfo=UTC),
    )

    page = await reader.search(limit=10, offset=100)

    assert page.rows == []
    assert page.total == 1


@pytest.mark.asyncio
async def test_search_pages_are_stable_under_showtime_and_id_ties(
    reader: PostgresScreeningReadGateway,
    screening_gateway: PostgresScreeningGateway,
    gateway: PostgresCinemaGateway,
    movie_gateway: PostgresMovieGateway,
) -> None:
    """Rows order by showtime then id, so a page boundary splits a tie without loss."""
    await _seed_parents(gateway, movie_gateway)
    # The two 19:00 rows differ by movie, since (cinema, movie, showtime) is unique.
    for screening_id, movie_id, hour in (
        ("scr-d", "mov-001", 20),
        ("scr-b", "mov-002", 19),
        ("scr-c", "mov-001", 18),
        ("scr-a", "mov-001", 19),
    ):
        await screening_gateway.save(
            screening_id=screening_id,
            movie_id=movie_id,
            cinema_id="cin-001",
            showtime=datetime(2026, 6, 7, hour, 0, tzinfo=UTC),
        )

    first = await reader.search(limit=2, offset=0)
    second = await reader.search(limit=2, offset=2)

    assert first.total == second.total == 4
    assert [row["id"] for row in first.rows] == ["scr-c", "scr-a"]
    assert [row["id"] for row in second.rows] == ["scr-b", "scr-d"]
