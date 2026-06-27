"""Database connection management."""

from __future__ import annotations

import re
import urllib.parse

import asyncpg

from marquise.infrastructure.supabase.config import Settings


def sanitize_dsn(dsn: str) -> str:
    """Percent-encode the password portion of a PostgreSQL DSN.

    Some providers (e.g. Supabase) use special characters in passwords
    that must be URL-encoded before asyncpg can parse the connection string.

    The regex matches from right to left: the host is the last ``@``-delimited
    segment before the first ``/`` (or end-of-string), so ``@`` characters
    inside the password are handled correctly.

    Args:
        dsn: The raw PostgreSQL DSN (``postgresql://user:pass@host/db``).

    Returns:
        The DSN with the password component percent-encoded.
    """
    match = re.match(
        r"^postgresql://(?P<user>[^:]+):(?P<password>.+)@(?P<host>[^/]+)(?P<rest>/.*)?$",
        dsn,
        re.DOTALL,
    )
    if match is None:
        return dsn
    raw_password = match["password"]
    safe_password = urllib.parse.quote(raw_password, safe="")
    rest = match["rest"] or ""
    return f"postgresql://{match['user']}:{safe_password}@{match['host']}{rest}"


class Database:
    """Manages an asyncpg connection pool for Supabase PostgreSQL.

    Handles pool lifecycle (connect / disconnect) and provides access
    to the underlying pool object.

    Attributes:
        pool: The asyncpg connection pool (only available after connect).
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the database manager.

        Args:
            settings: Application settings containing the DSN.
        """
        self._dsn: str = sanitize_dsn(settings.database_url)
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Open the connection pool."""
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)

    async def disconnect(self) -> None:
        """Close the connection pool and release all resources."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        """Return the connection pool.

        Returns:
            The active asyncpg pool.

        Raises:
            RuntimeError: If the pool has not been started via ``connect()``.
        """
        if self._pool is None:
            raise RuntimeError("Database not connected")
        return self._pool
