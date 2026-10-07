"""Atomic account/key serialization and write-session lifetime in PostgreSQL."""

import json
from asyncio import timeout
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from hashlib import sha256

import asyncpg

from marquise.application.transactions.screening_write import (
    ScreeningWriteSession,
    ScreeningWriteTransaction,
)
from marquise.application.use_cases.write_screening import ScreeningWriteBusyError
from marquise.infrastructure.supabase.connection_pool import ConnectionPool


class SupabaseScreeningWriteTransaction(ScreeningWriteTransaction):
    """Infrastructure transaction mechanics with an injected session factory."""

    def __init__(
        self,
        pool: ConnectionPool,
        session_factory: Callable[
            [asyncpg.Connection, str, str], ScreeningWriteSession
        ],
    ) -> None:
        """Inject acquisition and composition without hidden repositories."""
        self._pool = pool
        self._session_factory = session_factory

    @asynccontextmanager
    async def open(
        self, account: str, key: str
    ) -> AsyncIterator[ScreeningWriteSession]:
        """Serialize equivalent keys, then commit or roll back the entire session."""
        # Stable, unambiguous account/key hashing; advisory collisions only cause
        # extra waiting, never shared replay data (which uses exact account/key).
        lock_id = int.from_bytes(
            sha256(json.dumps([account, key]).encode()).digest()[:8], signed=True
        )
        async with AsyncExitStack() as stack:
            try:
                # Pool contention counts toward the same acquisition deadline.
                async with timeout(5):
                    connection = await stack.enter_async_context(self._pool.acquire())
                    await stack.enter_async_context(
                        connection.transaction(isolation="read_committed")
                    )
                    await connection.execute(
                        "SELECT set_config('lock_timeout', '5s', true)"
                    )
                    await connection.execute(
                        "SELECT pg_advisory_xact_lock($1::bigint)", lock_id
                    )
            except (TimeoutError, asyncpg.exceptions.LockNotAvailableError) as exc:
                raise ScreeningWriteBusyError(
                    "Screening write is still in progress; retry with the same key"
                ) from exc
            # The acquisition deadline must not cancel an accepted mutation.
            await connection.execute("SELECT set_config('lock_timeout', '0', true)")
            yield self._session_factory(connection, account, key)
