"""Database regressions for screening mutations (requires integration fixtures)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import asyncpg
import pytest

from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import SupabaseScreeningGateway
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningExternalIdConflictGatewayError,
)

SHOWTIME = datetime(2026, 6, 7, 19, 30, tzinfo=UTC)


async def _seed(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Seed a screening and alternate parents for mutation checks."""
    await gateway.save(cinema_id="cin-old", name="Old Cinema", address=None, city=None)
    await gateway.save(cinema_id="cin-new", name="New Cinema", address=None, city=None)
    await movie_gateway.save(movie_id="mov-old", title="Old Movie")
    await movie_gateway.save(movie_id="mov-new", title="New Movie")
    await screening_gateway.save(
        screening_id="scr-mutation",
        movie_id="mov-old",
        cinema_id="cin-old",
        showtime=SHOWTIME,
        room="Old Room",
        language="French",
        external_id="old-id",
    )


@pytest.mark.asyncio
async def test_partial_replace_preserves_concurrent_parent_change(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """A stale snapshot cannot restore omitted parent or metadata columns."""
    await _seed(gateway, movie_gateway, screening_gateway)
    await screening_gateway.replace(
        screening_id="scr-mutation",
        movie_id="mov-new",
        cinema_id="cin-new",
        showtime=SHOWTIME,
        language="English",
        fields=frozenset({"movie_id", "cinema_id", "language"}),
    )
    result = await screening_gateway.replace(
        screening_id="scr-mutation",
        movie_id="mov-old",
        cinema_id="cin-old",
        showtime=SHOWTIME,
        room=None,
        language="French",
        fields=frozenset({"room"}),
    )
    assert result is not None
    assert result["room"] is None
    assert result["language"] == "English"
    assert result["movie__id"] == "mov-new"
    assert result["movie__title"] == "New Movie"
    assert result["cinema__id"] == "cin-new"
    assert result["cinema__name"] == "New Cinema"
    assert result == await screening_gateway.find_by_id("scr-mutation")


@pytest.mark.asyncio
async def test_partial_replace_sees_parent_created_while_update_waits(
    db_pool: asyncpg.Pool,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """A parent committed after the UPDATE snapshot still appears in the result."""
    await _seed(gateway, movie_gateway, screening_gateway)
    replacement: asyncio.Task[dict | None] | None = None
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.fetchrow(
                    'SELECT id FROM "marquise-test".screenings '
                    "WHERE id = 'scr-mutation' FOR UPDATE"
                )
                replacement = asyncio.create_task(
                    screening_gateway.replace(
                        screening_id="scr-mutation",
                        movie_id="mov-old",
                        cinema_id="cin-old",
                        showtime=SHOWTIME,
                        language="English",
                        fields=frozenset({"language"}),
                    )
                )

                async def wait_for_update_lock() -> None:
                    while not await conn.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM pg_stat_activity
                            WHERE pid <> pg_backend_pid()
                                AND wait_event_type = 'Lock'
                                AND query LIKE '%UPDATE "marquise-test".screenings%'
                        )
                        """
                    ):
                        if replacement is not None and replacement.done():
                            await replacement
                            pytest.fail("Replacement did not wait for the row lock")
                        await asyncio.sleep(0.01)

                await asyncio.wait_for(wait_for_update_lock(), timeout=5)
                await conn.execute(
                    """
                    INSERT INTO "marquise-test".movies (id, title)
                    VALUES ('mov-concurrent', 'Concurrent Movie');
                    UPDATE "marquise-test".screenings
                    SET movie_id = 'mov-concurrent' WHERE id = 'scr-mutation';
                    """
                )
        result = await asyncio.wait_for(replacement, timeout=5)
    finally:
        if replacement is not None and not replacement.done():
            replacement.cancel()
            await asyncio.gather(replacement, return_exceptions=True)
    assert result is not None
    assert result["movie__id"] == "mov-concurrent"
    assert result["movie__title"] == "Concurrent Movie"
    assert result["language"] == "English"
    assert result == await screening_gateway.find_by_id("scr-mutation")


@pytest.mark.asyncio
async def test_empty_replace_mask_does_not_write(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """An empty patch returns the stored row without applying stale values."""
    await _seed(gateway, movie_gateway, screening_gateway)
    before = await screening_gateway.find_by_id("scr-mutation")
    result = await screening_gateway.replace(
        screening_id="scr-mutation",
        movie_id="missing",
        cinema_id="missing",
        showtime=SHOWTIME,
        fields=frozenset(),
    )
    assert result == before


@pytest.mark.asyncio
async def test_replace_external_id_conflict_is_distinct(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """External-ID collisions are not mislabeled as identity collisions."""
    await _seed(gateway, movie_gateway, screening_gateway)
    await screening_gateway.save(
        screening_id="scr-other",
        movie_id="mov-new",
        cinema_id="cin-new",
        showtime=SHOWTIME,
        external_id="taken-id",
    )
    with pytest.raises(ScreeningExternalIdConflictGatewayError):
        await screening_gateway.replace(
            screening_id="scr-mutation",
            movie_id="mov-old",
            cinema_id="cin-old",
            showtime=SHOWTIME,
            external_id="taken-id",
            fields=frozenset({"external_id"}),
        )
    result = await screening_gateway.find_by_id("scr-mutation")
    assert result is not None
    assert result["external_id"] == "old-id"


@pytest.mark.asyncio
async def test_replace_unknown_unique_constraint_propagates(
    db_pool: asyncpg.Pool,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """An unrecognized uniqueness failure retains its database error."""
    await _seed(gateway, movie_gateway, screening_gateway)
    await screening_gateway.save(
        screening_id="scr-other",
        movie_id="mov-new",
        cinema_id="cin-new",
        showtime=SHOWTIME,
        room="Taken Room",
    )
    async with db_pool.acquire() as conn:
        await conn.execute(
            'ALTER TABLE "marquise-test".screenings '
            "ADD CONSTRAINT mutation_room_unique UNIQUE (room)"
        )
    try:
        with pytest.raises(asyncpg.UniqueViolationError) as raised:
            await screening_gateway.replace(
                screening_id="scr-mutation",
                movie_id="mov-old",
                cinema_id="cin-old",
                showtime=SHOWTIME,
                room="Taken Room",
                fields=frozenset({"room"}),
            )
        assert raised.value.as_dict()["constraint_name"] == "mutation_room_unique"
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute(
                'ALTER TABLE "marquise-test".screenings '
                "DROP CONSTRAINT mutation_room_unique"
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("keep_other", [False, True])
async def test_delete_cleans_only_its_orphan_movie(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
    keep_other: bool,
) -> None:
    """The parent disappears only when its last screening is deleted."""
    await _seed(gateway, movie_gateway, screening_gateway)
    if keep_other:
        await screening_gateway.save(
            screening_id="scr-other",
            movie_id="mov-old",
            cinema_id="cin-new",
            showtime=SHOWTIME,
        )
    await screening_gateway.delete("scr-mutation")
    assert await screening_gateway.find_by_id("scr-mutation") is None
    assert (await movie_gateway.find_by_id("mov-old") is not None) == keep_other
    assert await movie_gateway.find_by_id("mov-new") is not None
    assert await gateway.find_by_id("cin-old") is not None
    if keep_other:
        assert await screening_gateway.find_by_id("scr-other") is not None


@pytest.mark.asyncio
async def test_concurrent_last_screening_deletes_clean_parent(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Concurrent deletes serialize parent cleanup without retaining an orphan."""
    await _seed(gateway, movie_gateway, screening_gateway)
    await screening_gateway.save(
        screening_id="scr-other",
        movie_id="mov-old",
        cinema_id="cin-new",
        showtime=SHOWTIME,
    )
    await asyncio.wait_for(
        asyncio.gather(
            screening_gateway.delete("scr-mutation"),
            screening_gateway.delete("scr-other"),
        ),
        timeout=5,
    )
    assert await movie_gateway.find_by_id("mov-old") is None
    assert await screening_gateway.find_by_id("scr-other") is None


@pytest.mark.asyncio
async def test_delete_waits_for_inflight_fk_insert_and_preserves_it(
    db_pool: asyncpg.Pool,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Cleanup takes a fresh snapshot after waiting for a parent's FK lock."""
    await _seed(gateway, movie_gateway, screening_gateway)
    deletion: asyncio.Task[None] | None = None
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.fetchrow(
                    'SELECT id FROM "marquise-test".movies '
                    "WHERE id = 'mov-old' FOR KEY SHARE"
                )
                deletion = asyncio.create_task(screening_gateway.delete("scr-mutation"))

                async def wait_for_cleanup_lock() -> None:
                    while not await conn.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM pg_stat_activity
                            WHERE pid <> pg_backend_pid()
                                AND wait_event_type = 'Lock'
                                AND query LIKE '%"marquise-test".movies%FOR UPDATE%'
                        )
                        """
                    ):
                        if deletion is not None and deletion.done():
                            await deletion
                            pytest.fail("Deletion did not wait for the parent lock")
                        await asyncio.sleep(0.01)

                await asyncio.wait_for(wait_for_cleanup_lock(), timeout=5)
                await conn.execute(
                    """
                    INSERT INTO "marquise-test".screenings
                        (id, movie_id, cinema_id, showtime)
                    VALUES ('scr-inflight', 'mov-old', 'cin-new', $1)
                    """,
                    SHOWTIME.replace(tzinfo=None),
                )
        await asyncio.wait_for(deletion, timeout=5)
    finally:
        if deletion is not None and not deletion.done():
            deletion.cancel()
            await asyncio.gather(deletion, return_exceptions=True)
    assert await movie_gateway.find_by_id("mov-old") is not None
    assert await screening_gateway.find_by_id("scr-inflight") is not None
    assert await screening_gateway.find_by_id("scr-mutation") is None


@pytest.mark.asyncio
async def test_orphan_cleanup_failure_rolls_back_screening_delete(
    db_pool: asyncpg.Pool,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """A failed movie cleanup cannot leave the screening deletion committed."""
    await _seed(gateway, movie_gateway, screening_gateway)
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE FUNCTION "marquise-test".reject_mutation_cleanup()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'cleanup rejected';
            END;
            $$;
            CREATE TRIGGER reject_mutation_cleanup BEFORE DELETE
            ON "marquise-test".movies FOR EACH ROW
            EXECUTE FUNCTION "marquise-test".reject_mutation_cleanup();
            """
        )
    try:
        with pytest.raises(asyncpg.RaiseError, match="cleanup rejected"):
            await screening_gateway.delete("scr-mutation")
        assert await screening_gateway.find_by_id("scr-mutation") is not None
        assert await movie_gateway.find_by_id("mov-old") is not None
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute(
                'DROP TRIGGER reject_mutation_cleanup ON "marquise-test".movies; '
                'DROP FUNCTION "marquise-test".reject_mutation_cleanup();'
            )


@pytest.mark.asyncio
async def test_delete_uses_actual_reparented_movie(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Cleanup targets the deleted row's parent, not an earlier read snapshot."""
    await _seed(gateway, movie_gateway, screening_gateway)
    await screening_gateway.replace(
        screening_id="scr-mutation",
        movie_id="mov-new",
        cinema_id="cin-old",
        showtime=SHOWTIME,
        fields=frozenset({"movie_id"}),
    )
    await screening_gateway.delete("scr-mutation")
    assert await movie_gateway.find_by_id("mov-new") is None
    assert await movie_gateway.find_by_id("mov-old") is not None
