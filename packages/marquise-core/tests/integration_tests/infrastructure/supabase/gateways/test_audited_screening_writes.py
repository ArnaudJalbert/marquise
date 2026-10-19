"""Audited write atomicity/concurrency against an isolated PostgreSQL database."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

import asyncpg
import pytest
import pytest_asyncio

from marquise.application.transactions.screening_write import ScreeningWriteSession
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.application.use_cases.write_screening import (
    ScreeningIdempotencyConflictError,
    ScreeningWriteBusyError,
    ScreeningWriteContext,
    WriteScreeningUseCase,
)
from marquise.infrastructure.di.screening_write import build_write_screening_use_case

SCHEMA = '"marquise-test"'
NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)


@pytest_asyncio.fixture
async def writer(db_pool: asyncpg.Pool) -> WriteScreeningUseCase:
    """Provision only the isolated test schema and seed parents for actual writes."""
    async with db_pool.acquire() as connection:
        await connection.execute(Path("scripts/marquise-test-schema.sql").read_text())
        await connection.execute(
            f"TRUNCATE {SCHEMA}.screening_write_audit, {SCHEMA}.screening_write_results"
        )
        await connection.execute(
            f"INSERT INTO {SCHEMA}.movies (id, title) VALUES ('mov-1', 'Movie One')"
        )
        await connection.execute(
            f"INSERT INTO {SCHEMA}.cinemas (id, name) VALUES ('cin-1', 'Cinema One')"
        )
    return build_write_screening_use_case(db_pool, "marquise-test")


def request(
    key: str = "create-1", account: str = "editor-1"
) -> WriteScreeningUseCase.InputData:
    """One intended creation, with a distinct key per new operation."""
    return WriteScreeningUseCase.InputData(
        context=ScreeningWriteContext(account=account, key=key, reason="Publish"),
        mutation=CreateScreeningUseCase.InputData(
            movie_id="mov-1", cinema_id="cin-1", showtime=NOW
        ),
    )


@pytest.mark.asyncio
async def test_concurrent_creation_has_one_mutation_audit_and_result(
    writer: WriteScreeningUseCase, db_pool: asyncpg.Pool
) -> None:
    """Concurrent duplicates receive one saved success and create one history row."""
    results = await asyncio.gather(*(writer.execute(request()) for _ in range(8)))
    assert all(result == results[0] for result in results)
    async with db_pool.acquire() as connection:
        assert (
            await connection.fetchval(f"SELECT count(*) FROM {SCHEMA}.screenings") == 1
        )
        assert (
            await connection.fetchval(
                f"SELECT count(*) FROM {SCHEMA}.screening_write_results"
            )
            == 1
        )
        audit = await connection.fetchrow(
            f"SELECT * FROM {SCHEMA}.screening_write_audit"
        )
        assert audit["account"] == "editor-1"
        assert audit["operation"] == "create"
        assert audit["before_values"] is None
        assert json.loads(audit["after_values"])["id"] == results[0].screening_id


@pytest.mark.asyncio
async def test_replay_survives_update_delete_and_orphan_cleanup(
    writer: WriteScreeningUseCase, db_pool: asyncpg.Pool
) -> None:
    """Original results and deletion history survive removal of Screening and Movie."""
    original = await writer.execute(request())
    update = WriteScreeningUseCase.InputData(
        context=replace(request().context, key="patch-1"),
        mutation=UpdateScreeningUseCase.InputData(
            screening_id=original.screening_id, room="Room 2"
        ),
    )
    updated = await writer.execute(update)
    delete = WriteScreeningUseCase.InputData(
        context=replace(request().context, key="delete-1"),
        mutation=DeleteScreeningUseCase.InputData(screening_id=original.screening_id),
    )
    deleted = await writer.execute(delete)
    assert await writer.execute(request()) == original
    assert await writer.execute(update) == updated
    assert await writer.execute(delete) == deleted
    async with db_pool.acquire() as connection:
        assert await connection.fetchval(f"SELECT count(*) FROM {SCHEMA}.movies") == 0
        assert (
            await connection.fetchval(f"SELECT count(*) FROM {SCHEMA}.screenings") == 0
        )
        audit = await connection.fetchrow(
            f"SELECT * FROM {SCHEMA}.screening_write_audit WHERE operation = 'delete'"
        )
        assert json.loads(audit["before_values"])["room"] == "Room 2"
        assert audit["after_values"] is None
        assert json.loads(audit["removed_movie"])["title"] == "Movie One"
        assert (
            await connection.fetchval(
                f"SELECT count(*) FROM {SCHEMA}.screening_write_audit"
            )
            == 3
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["screening_write_audit", "screening_write_results"])
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_journal_failure_rolls_back_change_and_leaves_key_reusable(
    writer: WriteScreeningUseCase, db_pool: asyncpg.Pool, table: str, operation: str
) -> None:
    """A real rejected journal INSERT rolls back changes, including orphan cleanup."""
    write = request(key="failed-1")
    if operation != "create":
        created = await writer.execute(request())
        mutation = (
            UpdateScreeningUseCase.InputData(
                screening_id=created.screening_id, room="Room 2"
            )
            if operation == "update"
            else DeleteScreeningUseCase.InputData(screening_id=created.screening_id)
        )
        write = replace(write, mutation=mutation)
    async with db_pool.acquire() as connection:
        await connection.execute(
            f"ALTER TABLE {SCHEMA}.{table} ADD CONSTRAINT reject_test_write "
            "CHECK (false) NOT VALID"
        )
    try:
        with pytest.raises(asyncpg.CheckViolationError):
            await writer.execute(write)
        async with db_pool.acquire() as connection:
            assert (
                await connection.fetchval(
                    f"SELECT count(*) FROM {SCHEMA}.screening_write_results "
                    "WHERE idempotency_key = 'failed-1'"
                )
                == 0
            )
            assert (
                await connection.fetchval(
                    f"SELECT count(*) FROM {SCHEMA}.screening_write_audit "
                    "WHERE idempotency_key = 'failed-1'"
                )
                == 0
            )
            assert (
                await connection.fetchval(f"SELECT count(*) FROM {SCHEMA}.movies") == 1
            )
            assert await connection.fetchval(
                f"SELECT count(*) FROM {SCHEMA}.screenings"
            ) == (0 if operation == "create" else 1)
            if operation == "update":
                assert (
                    await connection.fetchval(f"SELECT room FROM {SCHEMA}.screenings")
                    is None
                )
    finally:
        async with db_pool.acquire() as connection:
            await connection.execute(
                f"ALTER TABLE {SCHEMA}.{table} DROP CONSTRAINT reject_test_write"
            )
    assert (await writer.execute(write)).changed is True


@pytest.mark.asyncio
async def test_key_conflicts_and_account_scoping(writer: WriteScreeningUseCase) -> None:
    """One account cannot reuse intent; another account owns an independent key."""
    await writer.execute(request())
    changed = replace(request(), mutation=replace(request().mutation, room="New room"))
    with pytest.raises(ScreeningIdempotencyConflictError):
        await writer.execute(changed)
    separate = request(account="editor-2")
    separate = replace(
        separate, mutation=replace(separate.mutation, showtime=NOW.replace(hour=13))
    )
    assert (await writer.execute(separate)).screening_id


@pytest.mark.asyncio
async def test_empty_patch_is_replayable_without_history(
    writer: WriteScreeningUseCase, db_pool: asyncpg.Pool
) -> None:
    """Empty PATCH records success without producing audit or mutation effects."""
    created = await writer.execute(request())
    patch = WriteScreeningUseCase.InputData(
        context=replace(request().context, key="empty-1"),
        mutation=UpdateScreeningUseCase.InputData(screening_id=created.screening_id),
    )
    result = await writer.execute(patch)
    assert not result.changed
    assert await writer.execute(patch) == result
    async with db_pool.acquire() as connection:
        assert (
            await connection.fetchval(
                f"SELECT count(*) FROM {SCHEMA}.screening_write_audit"
            )
            == 1
        )
        assert (
            await connection.fetchval(
                f"SELECT count(*) FROM {SCHEMA}.screening_write_results"
            )
            == 2
        )


@pytest.mark.asyncio
async def test_pool_wait_is_bounded_and_retryable(
    writer: WriteScreeningUseCase, db_pool: asyncpg.Pool
) -> None:
    """Connection contention cannot turn the five-second wait into an unbounded wait."""
    async with db_pool.acquire(), db_pool.acquire():
        started = monotonic()
        with pytest.raises(ScreeningWriteBusyError):
            await asyncio.wait_for(writer.execute(request()), timeout=6)
        assert monotonic() - started < 6
    assert (await writer.execute(request())).changed


@pytest.mark.asyncio
async def test_concurrent_edits_record_the_state_they_change(
    writer: WriteScreeningUseCase, db_pool: asyncpg.Pool
) -> None:
    """Concurrent target edits form an accurate before/after chain across keys."""
    created = await writer.execute(request())
    edits = [
        WriteScreeningUseCase.InputData(
            context=replace(request().context, key=f"patch-{room.replace(' ', '-')}"),
            mutation=UpdateScreeningUseCase.InputData(
                screening_id=created.screening_id, room=room
            ),
        )
        for room in ("Room 1", "Room 2")
    ]
    await asyncio.gather(*(writer.execute(edit) for edit in edits))
    async with db_pool.acquire() as connection:
        audits = await connection.fetch(
            f"SELECT before_values, after_values FROM {SCHEMA}.screening_write_audit "
            "WHERE operation = 'update' ORDER BY id"
        )
    assert len(audits) == 2
    assert json.loads(audits[0]["before_values"])["room"] is None
    assert (
        json.loads(audits[1]["before_values"])["room"]
        == json.loads(audits[0]["after_values"])["room"]
    )
    assert (
        json.loads(audits[1]["after_values"])["room"]
        != json.loads(audits[0]["after_values"])["room"]
    )


@pytest.mark.asyncio
async def test_concurrent_conflicting_key_has_one_winner(
    writer: WriteScreeningUseCase, db_pool: asyncpg.Pool
) -> None:
    """Different intent sharing one key cannot create two successful operations."""
    other = replace(request(), mutation=replace(request().mutation, room="Room 2"))
    results = await asyncio.gather(
        writer.execute(request()), writer.execute(other), return_exceptions=True
    )
    assert (
        sum(isinstance(result, ScreeningIdempotencyConflictError) for result in results)
        == 1
    )
    async with db_pool.acquire() as connection:
        assert (
            await connection.fetchval(
                f"SELECT count(*) FROM {SCHEMA}.screening_write_audit"
            )
            == 1
        )


@pytest.mark.asyncio
async def test_duplicate_lock_wait_times_out_without_cancelling_first_write(
    writer: WriteScreeningUseCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slow first write stays valid while its duplicate gets a retryable error."""
    locked = asyncio.Event()
    release = asyncio.Event()
    transaction = writer._transaction
    original_open = transaction.open

    @asynccontextmanager
    async def hold_first_lock(
        account: str, key: str
    ) -> AsyncIterator[ScreeningWriteSession]:
        async with original_open(account, key) as session:
            if not locked.is_set():
                locked.set()
                await release.wait()
            yield session

    monkeypatch.setattr(transaction, "open", hold_first_lock)
    first = asyncio.create_task(writer.execute(request()))
    try:
        await asyncio.wait_for(locked.wait(), timeout=10)
        with pytest.raises(ScreeningWriteBusyError):
            await writer.execute(request())
        release.set()
        original = await first
        assert await writer.execute(request()) == original
    finally:
        release.set()
        await first
