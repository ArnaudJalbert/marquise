"""PostgreSQL persistence for one transaction-scoped screening write."""

import json
from datetime import datetime

import asyncpg


class SupabaseScreeningWriteGateway:
    """Execute only persistence/locking mechanics, never construct audit policy."""

    def __init__(
        self, connection: asyncpg.Connection, account: str, key: str, schema: str
    ) -> None:
        """Bind to the composition root's active transaction connection."""
        self._connection = connection
        self._account = account
        self._key = key
        self._schema = schema

    async def lock_target(self, screening_id: str, *, lock_movie: bool) -> None:
        """Lock screening, then its movie when deletion can remove that movie."""
        row = await self._connection.fetchrow(
            f'SELECT movie_id FROM "{self._schema}".screenings '
            "WHERE id = $1 FOR UPDATE",
            screening_id,
        )
        if row is not None and lock_movie:
            await self._connection.fetchrow(
                f'SELECT id FROM "{self._schema}".movies WHERE id = $1 FOR UPDATE',
                row["movie_id"],
            )

    async def find_replay(self) -> dict | None:
        """Read durable replay data for the already serialized account/key."""
        row = await self._connection.fetchrow(
            f'SELECT fingerprint, result FROM "{self._schema}".screening_write_results '
            "WHERE account = $1 AND idempotency_key = $2",
            self._account,
            self._key,
        )
        if row is None:
            return None
        return {"fingerprint": row["fingerprint"], "result": json.loads(row["result"])}

    async def save_audit(self, record: dict) -> None:
        """Insert application-built history in the active transaction."""
        await self._connection.execute(
            f'''INSERT INTO "{self._schema}".screening_write_audit
            (account, idempotency_key, operation, target_id, recorded_at, reason,
             before_values, after_values, removed_movie)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb)''',
            record["account"],
            record["key"],
            record["operation"],
            record["target"],
            record["timestamp"],
            record["reason"],
            *(
                json.dumps(record[field], default=datetime.isoformat)
                if record[field] is not None
                else None
                for field in ("before", "after", "removed_movie")
            ),
        )

    async def save_replay(self, replay: dict) -> None:
        """Insert the result atomically; account/key uniqueness is a DB invariant."""
        await self._connection.execute(
            f'''INSERT INTO "{self._schema}".screening_write_results
            (account, idempotency_key, fingerprint, result)
            VALUES ($1, $2, $3, $4::jsonb)''',
            self._account,
            self._key,
            replay["fingerprint"],
            json.dumps(replay["result"], default=datetime.isoformat),
        )
