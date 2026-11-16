"""Guarded merges against disposable PostgreSQL, without shared schema changes."""

from dataclasses import replace

import asyncpg
import pytest

from marquise.application.movie_workflows import MergeMoviesInputData
from marquise.infrastructure.supabase.gateways.movie_merge import (
    SupabaseMovieMergeGateway,
)

TABLE = '"marquise-test"'


async def seed(
    pool: asyncpg.Pool, titles: tuple[str, ...] = ("Fjord", "Fjord VF", "Fjord VO")
) -> SupabaseMovieMergeGateway:
    """Seed linked canonical and independent source screenings with all fields."""
    async with pool.acquire() as conn:
        await conn.execute(
            f"INSERT INTO {TABLE}.source_definitions(name,display_name) "
            "VALUES ('source','Source')"
        )
        await conn.execute(
            f"INSERT INTO {TABLE}.cinemas(id,name) VALUES ('cinema','Cinema')"
        )
        for index, title in enumerate(titles):
            await conn.execute(
                f"INSERT INTO {TABLE}.movies "
                "(id,title,tmdb_id,release_year,directors,duration_minutes) "
                "VALUES ($1,$2,$3,2026,'Director',100)",
                str(index),
                title,
                "1401459" if index == 0 else None,
            )
            await conn.execute(
                f"INSERT INTO {TABLE}.screenings "
                "(id,movie_id,cinema_id,showtime,external_id,source_name,"
                "ticket_url,room,language) VALUES ($1,$2,'cinema', "
                "'2026-11-01 12:00'::timestamp + $3 * interval '1 hour',"
                "$1,'source','https://tickets.test','Room','fr')",
                "s" + str(index),
                str(index),
                index,
            )
    return SupabaseMovieMergeGateway(pool, "marquise-test")


async def rows(pool: asyncpg.Pool) -> list[dict]:
    """Capture every screening field for exact preservation checks."""
    async with pool.acquire() as conn:
        return [
            dict(row)
            for row in await conn.fetch(f"SELECT * FROM {TABLE}.screenings ORDER BY id")
        ]


@pytest.mark.parametrize(
    "titles", [("Fjord", "Fjord VF", "Fjord VO"), ("Fleak", "Le Monde de Wishy")]
)
@pytest.mark.asyncio
async def test_stable_screenings_and_idempotent_retry(
    db_pool: asyncpg.Pool, titles: tuple[str, ...]
) -> None:
    """Three Fjord rows and translated pairs merge without changing source fields."""
    gateway = await seed(db_pool, titles)
    duplicates = tuple(str(i) for i in range(1, len(titles)))
    before = await rows(db_pool)
    preview = await gateway.merge(MergeMoviesInputData("0", duplicates))
    assert preview.status == "preview"
    assert await rows(db_pool) == before
    request = MergeMoviesInputData("0", duplicates, preview.snapshots)
    result = await gateway.merge(request)
    assert result.status == "applied"
    assert result.moved_screening_ids == tuple("s" + i for i in duplicates)
    assert await rows(db_pool) == [dict(row, movie_id="0") for row in before]
    async with db_pool.acquire() as conn:
        assert await conn.fetchval(f"SELECT count(*) FROM {TABLE}.movies") == 1
        assert await conn.fetchval(f"SELECT tmdb_id FROM {TABLE}.movies") == "1401459"
    retry = await gateway.merge(request)
    assert retry.status == "applied"
    assert retry.moved_screening_ids == result.moved_screening_ids
    async with db_pool.acquire() as conn:
        await conn.execute(
            f"UPDATE {TABLE}.screenings SET room='changed' WHERE id='s1'"
        )
    assert (await gateway.merge(request)).status == "blocked"


@pytest.mark.asyncio
async def test_collision_is_read_only_and_atomic(db_pool: asyncpg.Pool) -> None:
    """Colliding screening slots remain separate; no IDs or external IDs disappear."""
    gateway = await seed(db_pool)
    async with db_pool.acquire() as conn:
        await conn.execute(
            f"UPDATE {TABLE}.screenings SET showtime='2026-11-01 12:00' WHERE id='s1'"
        )
    before = await rows(db_pool)
    preview = await gateway.merge(MergeMoviesInputData("0", ("1", "2")))
    assert preview.status == "blocked"
    assert "s0,s1" in str(preview.blockers)
    assert (
        await gateway.merge(MergeMoviesInputData("0", ("1", "2"), preview.snapshots))
    ).status == "blocked"
    assert await rows(db_pool) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE {t}.movies SET description='changed' WHERE id='1'",
        "UPDATE {t}.movies SET tmdb_id='different' WHERE id='1'",
        "UPDATE {t}.screenings SET ticket_url='changed' WHERE id='s1'",
        "UPDATE {t}.screenings SET language='en' WHERE id='s1'",
        "UPDATE {t}.screenings SET external_id='changed' WHERE id='s1'",
        "DELETE FROM {t}.screenings WHERE id='s1'",
    ],
)
@pytest.mark.asyncio
async def test_stale_snapshot_blocks_all_changes(
    db_pool: asyncpg.Pool, mutation: str
) -> None:
    """Metadata, identity and screening changes invalidate approval atomically."""
    gateway = await seed(db_pool)
    preview = await gateway.merge(MergeMoviesInputData("0", ("1", "2")))
    async with db_pool.acquire() as conn:
        await conn.execute(mutation.format(t=TABLE))
    before = await rows(db_pool)
    assert (
        await gateway.merge(MergeMoviesInputData("0", ("1", "2"), preview.snapshots))
    ).status == "blocked"
    assert await rows(db_pool) == before


@pytest.mark.asyncio
async def test_unexpected_cascade_reference_blocks(db_pool: asyncpg.Pool) -> None:
    """A newly introduced cascading reference cannot be silently deleted."""
    gateway = await seed(db_pool)
    preview = await gateway.merge(MergeMoviesInputData("0", ("1", "2")))
    async with db_pool.acquire() as conn:
        await conn.execute(
            f"CREATE TABLE {TABLE}.merge_test_refs "
            f"(movie_id text REFERENCES {TABLE}.movies(id) ON DELETE CASCADE)"
        )
        await conn.execute(f"INSERT INTO {TABLE}.merge_test_refs VALUES ('1')")
    try:
        blocked = await gateway.merge(
            MergeMoviesInputData("0", ("1", "2"), preview.snapshots)
        )
        assert blocked.status == "blocked"
        assert "merge_test_refs" in str(blocked.blockers)
        assert (
            (await gateway.merge(MergeMoviesInputData("0", ("1", "2"))))
            .snapshots[0]
            .unresolved_references
        )
        async with db_pool.acquire() as conn:
            assert (
                await conn.fetchval(f"SELECT count(*) FROM {TABLE}.merge_test_refs")
                == 1
            )
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute(f"DROP TABLE {TABLE}.merge_test_refs")


@pytest.mark.asyncio
async def test_delete_failure_rolls_back_screening_moves(db_pool: asyncpg.Pool) -> None:
    """A failure after reassignment rolls back the entire affected merge."""
    gateway = await seed(db_pool)
    preview = await gateway.merge(MergeMoviesInputData("0", ("1", "2")))
    before = await rows(db_pool)
    async with db_pool.acquire() as conn:
        await conn.execute(f"""
            CREATE FUNCTION {TABLE}.merge_test_fail()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'refuse delete' USING ERRCODE='23514'; END $$;
            CREATE TRIGGER merge_test_fail BEFORE DELETE ON {TABLE}.movies
            FOR EACH ROW EXECUTE FUNCTION {TABLE}.merge_test_fail();
        """)
    try:
        assert (
            await gateway.merge(
                MergeMoviesInputData("0", ("1", "2"), preview.snapshots)
            )
        ).status == "blocked"
        assert await rows(db_pool) == before
        async with db_pool.acquire() as conn:
            assert await conn.fetchval(f"SELECT count(*) FROM {TABLE}.movies") == 3
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute(
                f"DROP TRIGGER merge_test_fail ON {TABLE}.movies; "
                f"DROP FUNCTION {TABLE}.merge_test_fail()"
            )


@pytest.mark.asyncio
async def test_approval_binds_survivor_and_exact_snapshot(
    db_pool: asyncpg.Pool,
) -> None:
    """Swapping canonical roles or altering approved fields cannot reuse a preview."""
    gateway = await seed(db_pool)
    preview = await gateway.merge(MergeMoviesInputData("0", ("1", "2")))
    assert (
        await gateway.merge(MergeMoviesInputData("1", ("0", "2"), preview.snapshots))
    ).status == "blocked"
    altered = (
        replace(preview.snapshots[0], tmdb_id="different"),
        *preview.snapshots[1:],
    )
    assert (
        await gateway.merge(MergeMoviesInputData("0", ("1", "2"), altered))
    ).status == "blocked"


@pytest.mark.asyncio
async def test_new_external_identity_owner_invalidates_approval(
    db_pool: asyncpg.Pool,
) -> None:
    """A linked owner introduced outside an unlinked group invalidates approval."""
    gateway = await seed(db_pool)
    async with db_pool.acquire() as conn:
        await conn.execute(f"UPDATE {TABLE}.movies SET tmdb_id=NULL")
    preview = await gateway.merge(MergeMoviesInputData("0", ("1", "2")))
    async with db_pool.acquire() as conn:
        await conn.execute(
            f"INSERT INTO {TABLE}.movies(id,title,tmdb_id) "
            "VALUES ('outside','Outside','1401459')"
        )
    before = await rows(db_pool)
    assert (
        await gateway.merge(MergeMoviesInputData("0", ("1", "2"), preview.snapshots))
    ).status == "blocked"
    assert await rows(db_pool) == before


@pytest.mark.asyncio
async def test_preview_preserves_comma_delimited_directors(
    db_pool: asyncpg.Pool,
) -> None:
    """A preview returns stored co-directors as separate names."""
    gateway = await seed(db_pool)
    async with db_pool.acquire() as conn:
        await conn.execute(
            f"UPDATE {TABLE}.movies SET directors = $1 WHERE id = '0'",
            "Director One,Director Two",
        )
    preview = await gateway.merge(MergeMoviesInputData("0", ("1", "2")))
    survivor = next(s for s in preview.snapshots if s.movie_id == "0")
    assert survivor.values.directors == ("Director One", "Director Two")
