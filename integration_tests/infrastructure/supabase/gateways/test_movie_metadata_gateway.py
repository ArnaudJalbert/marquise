"""Disposable PostgreSQL evidence for stable-ID metadata persistence."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest

from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.movie_metadata import (
    SupabaseMovieMetadataGateway,
)
from marquise.interface_adapters.repositories.protocols.movie_metadata import (
    MovieMetadataConflictError,
)

SCHEMA = "marquise-test"
STAMP = datetime(2026, 10, 30, 12, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.asyncio
async def test_stable_ids_source_screenings_and_lifecycle(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Pending source becomes enriched and refreshed without touching screenings."""
    await movie_gateway.save(
        "movie",
        "Source",
        directors="Source Director",
        description="Source synopsis",
    )
    async with db_pool.acquire() as conn:
        await conn.execute(
            f'INSERT INTO "{SCHEMA}".cinemas VALUES ($1, $2)', "cin", "Cinema"
        )
        await conn.execute(
            f'''INSERT INTO "{SCHEMA}".screenings
                (id, movie_id, cinema_id, showtime, ticket_url, room, language)
                VALUES ('screening', 'movie', 'cin', '2026-10-30 19:00',
                        'source-ticket', 'Room 1', 'fr')''',
        )
        before_screening = dict(
            await conn.fetchrow(f'SELECT * FROM "{SCHEMA}".screenings')
        )
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    pending = await gateway.get("movie")
    assert pending is not None
    assert pending["tmdb_id"] is None and pending["metadata_enriched_at"] is None
    updated = await gateway.update_metadata(
        "movie",
        pending["revision"],
        {
            "title": "Canonical",
            "description": None,
            "original_title": "Original",
            "release_year": 1976,
            "cast_members": "A,B",
            "duration_minutes": 98,
            "genres": "Horror",
            "origin_countries": "CA",
            "poster_url": "poster",
            "trailer_url": "trailer",
            "rating": "13+",
            "tmdb_rating": 8.1,
            "tmdb_vote_count": 1234,
        },
        "42",
        STAMP,
    )
    assert updated["id"] == "movie" and updated["screening_ids"] == ["screening"]
    assert updated["revision"] != pending["revision"]
    assert updated["title"] == "Canonical" and updated["tmdb_id"] == "42"
    assert updated["description"] == "Source synopsis"
    assert updated["directors"] == "Source Director"
    assert updated["metadata_enriched_at"] == STAMP
    assert (updated["tmdb_rating"], updated["tmdb_vote_count"]) == (8.1, 1234)
    assert await gateway.find_by_tmdb_id("42") == updated
    refreshed = await gateway.update_metadata(
        "movie",
        updated["revision"],
        {"description": "Refreshed"},
        "42",
        STAMP + timedelta(days=1),
    )
    assert refreshed["metadata_enriched_at"] == STAMP + timedelta(days=1)
    assert refreshed["revision"] != updated["revision"]
    assert (refreshed["tmdb_rating"], refreshed["tmdb_vote_count"]) == (8.1, 1234)
    async with db_pool.acquire() as conn:
        assert (
            dict(await conn.fetchrow(f'SELECT * FROM "{SCHEMA}".screenings'))
            == before_screening
        )


@pytest.mark.asyncio
async def test_legacy_known_identity_is_pending_and_list_order_is_stable(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Legacy ID-bearing rows can receive first enrichment and appear by ID order."""
    await movie_gateway.save("z", "Legacy", tmdb_id="42")
    await movie_gateway.save("a", "Another", tmdb_id="43")
    await movie_gateway.save("unlinked", "Unlinked")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    linked = await gateway.list_tmdb_movies()
    assert [row["id"] for row in linked] == ["a", "z"]
    assert all(row["metadata_enriched_at"] is None for row in linked)
    legacy = await gateway.find_by_tmdb_id("42")
    assert legacy is not None
    enriched = await gateway.update_metadata("z", legacy["revision"], {}, "42", STAMP)
    assert enriched["metadata_enriched_at"] == STAMP
    assert await gateway.get("absent") is None
    assert await gateway.find_by_tmdb_id("absent") is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "patch,identity",
    [
        ({"title": "Occupied"}, "42"),
        ({"description": "stolen"}, "43"),
    ],
)
async def test_collisions_roll_back_metadata_and_stamp(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
    patch: dict,
    identity: str,
) -> None:
    """Title and identity collisions leave both movies and completion unchanged."""
    await movie_gateway.save("target", "Source", description="original")
    await movie_gateway.save("owner", "Occupied", tmdb_id="43")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    before = await gateway.get("target")
    owner = await gateway.get("owner")
    assert before is not None
    with pytest.raises(MovieMetadataConflictError):
        await gateway.update_metadata(
            "target", before["revision"], patch, identity, STAMP
        )
    assert await gateway.get("target") == before
    assert await gateway.get("owner") == owner


@pytest.mark.asyncio
async def test_identity_reassignment_stale_and_missing_are_refused(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """A fresh revision cannot authorize identity theft; stale and missing IDs fail."""
    await movie_gateway.save("movie", "Source", tmdb_id="42")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    before = await gateway.get("movie")
    assert before is not None
    for movie_id, revision, identity in (
        ("movie", before["revision"], "43"),
        ("movie", "stale", "42"),
        ("missing", before["revision"], "42"),
    ):
        with pytest.raises(MovieMetadataConflictError):
            await gateway.update_metadata(movie_id, revision, {}, identity, STAMP)
    assert await gateway.get("movie") == before


@pytest.mark.asyncio
async def test_failed_refresh_keeps_previous_success(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """A database failure during refresh rolls back fields and last success time."""
    await movie_gateway.save("movie", "Source", tmdb_id="42")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    initial = await gateway.get("movie")
    assert initial is not None
    before = await gateway.update_metadata(
        "movie", initial["revision"], {}, "42", STAMP
    )
    async with db_pool.acquire() as conn:
        await conn.execute(
            f'''ALTER TABLE "{SCHEMA}".movies ADD CONSTRAINT test_failure
                CHECK (description IS DISTINCT FROM 'fail')''',
        )
    try:
        with pytest.raises(asyncpg.CheckViolationError):
            await gateway.update_metadata(
                "movie",
                before["revision"],
                {"title": "Changed", "description": "fail"},
                "42",
                STAMP + timedelta(days=1),
            )
        assert await gateway.get("movie") == before
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute(
                f'ALTER TABLE "{SCHEMA}".movies DROP CONSTRAINT test_failure'
            )


@pytest.mark.asyncio
async def test_racing_patches_only_one_revision_wins(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Concurrent writers cannot silently overwrite metadata from one snapshot."""
    await movie_gateway.save("movie", "Source")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    before = await gateway.get("movie")
    assert before is not None
    results = await asyncio.gather(
        *(
            gateway.update_metadata(
                "movie",
                before["revision"],
                {"description": f"winner-{i}"},
                "42",
                STAMP,
            )
            for i in range(2)
        ),
        return_exceptions=True,
    )
    winners = [row for row in results if isinstance(row, dict)]
    assert len(winners) == 1
    assert sum(isinstance(row, MovieMetadataConflictError) for row in results) == 1
    assert await gateway.get("movie") == winners[0]


@pytest.mark.asyncio
async def test_concurrent_identity_claim_has_one_owner(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Different movie locks still rely on unique identity ownership at commit."""
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    snapshots = []
    for movie_id in ("a", "b"):
        await movie_gateway.save(movie_id, movie_id)
        snapshots.append(await gateway.get(movie_id))
    results = await asyncio.gather(
        *(
            gateway.update_metadata(row["id"], row["revision"], {}, "42", STAMP)
            for row in snapshots
            if row is not None
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(row, dict) for row in results) == 1
    assert sum(isinstance(row, MovieMetadataConflictError) for row in results) == 1
    linked = await gateway.list_tmdb_movies()
    assert len(linked) == 1
    loser = await gateway.get("b" if linked[0]["id"] == "a" else "a")
    assert loser is not None and loser["metadata_enriched_at"] is None


@pytest.mark.asyncio
async def test_create_or_reuse_cannot_overwrite_completed_metadata(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Racing imports reuse the enriched row by title or identity without changes."""
    await movie_gateway.save("movie", "Source")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    before = await gateway.get("movie")
    assert before is not None
    enriched = await gateway.update_metadata(
        "movie",
        before["revision"],
        {"title": "Canonical", "description": "Provider"},
        "42",
        STAMP,
    )
    results = await asyncio.gather(
        *(
            movie_gateway.save(
                f"import-{index}",
                title,
                description="Source",
                tmdb_id=identity,
                update_existing=False,
            )
            for index, (title, identity) in enumerate(
                [
                    ("Canonical", None),
                    ("Alias", "42"),
                ]
            )
        )
    )
    assert all(
        row["id"] == "movie" and row["description"] == "Provider" for row in results
    )
    assert await gateway.get("movie") == enriched


@pytest.mark.asyncio
async def test_ordinary_movie_and_screening_writes_invalidate_revision(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Legacy saves and all screening changes invalidate the previous revision."""
    await movie_gateway.save("movie", "Source")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    previous = await gateway.get("movie")
    assert previous is not None
    statements = [
        f'''UPDATE "{SCHEMA}".movies SET description = 'edit' WHERE id = 'movie' ''',
        f'''INSERT INTO "{SCHEMA}".screenings (id, movie_id, cinema_id, showtime)
            VALUES ('screening', 'movie', 'cin', '2026-10-30 19:00')''',
        f'''UPDATE "{SCHEMA}".screenings SET room = 'changed'
            WHERE id = 'screening' ''',
        f'''DELETE FROM "{SCHEMA}".screenings WHERE id = 'screening' ''',
    ]
    async with db_pool.acquire() as conn:
        await conn.execute(
            f'''INSERT INTO "{SCHEMA}".cinemas VALUES ('cin', 'Cinema')'''
        )
    for sql in statements:
        async with db_pool.acquire() as conn:
            await conn.execute(sql)
        current = await gateway.get("movie")
        assert current is not None and current["revision"] != previous["revision"]
        with pytest.raises(MovieMetadataConflictError):
            await gateway.update_metadata(
                "movie", previous["revision"], {}, "42", STAMP
            )
        previous = current


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identity,stamp", [("", STAMP), ("42", STAMP.replace(tzinfo=None))]
)
async def test_invalid_write_inputs_do_not_stamp(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
    identity: str,
    stamp: datetime,
) -> None:
    """Empty identity and ambiguous timestamps are rejected before storage."""
    await movie_gateway.save("movie", "Source")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    before = await gateway.get("movie")
    assert before is not None
    with pytest.raises(ValueError):
        await gateway.update_metadata("movie", before["revision"], {}, identity, stamp)
    assert await gateway.get("movie") == before


@pytest.mark.asyncio
async def test_additive_migration_is_bounded_rerunnable_and_preserves_legacy(
    db_pool: asyncpg.Pool,
) -> None:
    """Migration retains every legacy field, never infers success and can rerun."""
    sql = (ROOT / "scripts/migrations/359-movie-enrichment-state.sql").read_text()
    assert "SET LOCAL lock_timeout = '5s'" in sql
    assert "SET LOCAL statement_timeout = '60s'" in sql
    async with db_pool.acquire() as conn:
        try:
            await conn.execute("CREATE SCHEMA migration_359")
            await conn.execute("""CREATE TABLE migration_359.movies
                (id TEXT PRIMARY KEY, title TEXT, tmdb_id TEXT UNIQUE)""")
            await conn.execute("""CREATE TABLE migration_359.screenings
                (id TEXT PRIMARY KEY,
                 movie_id TEXT REFERENCES migration_359.movies(id))""")
            await conn.execute(
                "INSERT INTO migration_359.movies VALUES ('legacy', 'Original', '42')"
            )
            migration = sql.replace("marquise.", "migration_359.")
            await conn.execute(migration)
            assert dict(await conn.fetchrow("SELECT * FROM migration_359.movies")) == {
                "id": "legacy",
                "title": "Original",
                "tmdb_id": "42",
                "metadata_enriched_at": None,
            }
            await conn.execute(
                "UPDATE migration_359.movies SET metadata_enriched_at = $1", STAMP
            )
            await conn.execute(migration)
            assert (
                await conn.fetchval(
                    "SELECT metadata_enriched_at FROM migration_359.movies"
                )
                == STAMP
            )
        finally:
            await conn.execute("ROLLBACK")
            await conn.execute("DROP SCHEMA IF EXISTS migration_359 CASCADE")


@pytest.mark.asyncio
async def test_fresh_schemas_are_rerunnable_with_nullable_timezone_stamp(
    db_pool: asyncpg.Pool,
) -> None:
    """The canonical bootstrap preserves nullable lifecycle state on rerun."""
    sql = (
        (ROOT / "scripts/marquise-schema.sql")
        .read_text()
        .replace("marquise", "fresh_359")
    )
    async with db_pool.acquire() as conn:
        try:
            await conn.execute(sql)
            await conn.execute(sql)
            row = await conn.fetchrow("""SELECT data_type, is_nullable, column_default
                FROM information_schema.columns WHERE table_schema = 'fresh_359'
                AND table_name = 'movies' AND column_name = 'metadata_enriched_at' """)
            assert dict(row) == {
                "data_type": "timestamp with time zone",
                "is_nullable": "YES",
                "column_default": None,
            }
        finally:
            await conn.execute("DROP SCHEMA IF EXISTS fresh_359 CASCADE")


@pytest.mark.asyncio
async def test_reference_round_trip_never_restores_an_old_revision(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Adding then deleting a screening cannot make an old approval valid again."""
    await movie_gateway.save("movie", "Source")
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    before = await gateway.get("movie")
    assert before is not None
    async with db_pool.acquire() as conn:
        await conn.execute(
            f'''INSERT INTO "{SCHEMA}".cinemas VALUES ('cin', 'Cinema')'''
        )
        await conn.execute(f'''INSERT INTO "{SCHEMA}".screenings
            (id, movie_id, cinema_id, showtime)
            VALUES ('screening', 'movie', 'cin', '2026-10-30 19:00')''')
        await conn.execute(
            f'''DELETE FROM "{SCHEMA}".screenings WHERE id = 'screening' '''
        )
    after = await gateway.get("movie")
    assert after is not None
    assert before["screening_ids"] == after["screening_ids"] == []
    assert before["revision"] != after["revision"]
    with pytest.raises(MovieMetadataConflictError):
        await gateway.update_metadata("movie", before["revision"], {}, "42", STAMP)


@pytest.mark.asyncio
async def test_migration_failure_rolls_back_all_additions(
    db_pool: asyncpg.Pool,
) -> None:
    """A missing prerequisite table leaves no partial columns or functions."""
    sql = (ROOT / "scripts/migrations/359-movie-enrichment-state.sql").read_text()
    async with db_pool.acquire() as conn:
        try:
            await conn.execute("CREATE SCHEMA failure_359")
            await conn.execute("CREATE TABLE failure_359.movies (id TEXT PRIMARY KEY)")
            with pytest.raises(asyncpg.UndefinedTableError):
                await conn.execute(sql.replace("marquise.", "failure_359."))
            await conn.execute("ROLLBACK")
            assert (
                await conn.fetchval("""SELECT count(*) FROM information_schema.columns
                WHERE table_schema = 'failure_359' AND table_name = 'movies' """)
                == 1
            )
            assert (
                await conn.fetchval("""SELECT count(*) FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'failure_359' """)
                == 0
            )
        finally:
            await conn.execute("ROLLBACK")
            await conn.execute("DROP SCHEMA IF EXISTS failure_359 CASCADE")


@pytest.mark.asyncio
async def test_reference_moves_invalidate_both_movies_and_rollback_markers(
    db_pool: asyncpg.Pool,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Moves invalidate both owners; rolled-back edits leave snapshots unchanged."""
    for movie_id in ("a", "b", "unrelated"):
        await movie_gateway.save(movie_id, movie_id)
    async with db_pool.acquire() as conn:
        await conn.execute(
            f'''INSERT INTO "{SCHEMA}".cinemas VALUES ('cin', 'Cinema')'''
        )
        await conn.execute(f'''INSERT INTO "{SCHEMA}".screenings
            (id, movie_id, cinema_id, showtime)
            VALUES ('screening', 'a', 'cin', '2026-10-30 19:00')''')
    gateway = SupabaseMovieMetadataGateway(db_pool, SCHEMA)
    before = {
        movie_id: await gateway.get(movie_id) for movie_id in ("a", "b", "unrelated")
    }
    async with db_pool.acquire() as conn:
        await conn.execute(f'''UPDATE "{SCHEMA}".screenings
            SET movie_id = 'b' WHERE id = 'screening' ''')
    for movie_id in ("a", "b"):
        row = await gateway.get(movie_id)
        old = before[movie_id]
        assert row is not None and old is not None
        assert row["revision"] != old["revision"]
    assert await gateway.get("unrelated") == before["unrelated"]
    moved = await gateway.get("b")
    async with db_pool.acquire() as conn:
        transaction = conn.transaction()
        await transaction.start()
        await conn.execute(
            f'''DELETE FROM "{SCHEMA}".screenings WHERE id = 'screening' '''
        )
        await transaction.rollback()
    assert await gateway.get("b") == moved
