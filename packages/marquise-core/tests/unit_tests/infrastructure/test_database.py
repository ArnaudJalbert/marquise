"""Unit tests for infrastructure database module."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, create_autospec

import asyncpg
import pytest

from marquise.infrastructure.supabase.config import Settings
from marquise.infrastructure.supabase.database import Database, sanitize_dsn

_TEST_SETTINGS = Settings(
    database_url="postgresql://user:pass@localhost:5432/test",
    tmdb_api_key="tmdb-key",
    schema="marquise",
)


def test_sanitize_dsn_clean_unchanged() -> None:
    """Verify a DSN without special characters is unchanged."""
    dsn = "postgresql://user:secret@localhost:5432/db"
    assert sanitize_dsn(dsn) == dsn


def test_sanitize_dsn_encodes_hash_in_password() -> None:
    """Verify a # in the password is percent-encoded as %23."""
    dsn = "postgresql://user:pw#abc@host:5432/db"
    result = sanitize_dsn(dsn)
    assert "#" not in result.split("@")[0]
    assert "%23" in result


def test_sanitize_dsn_encodes_at_in_password() -> None:
    """Verify an @ in the password is percent-encoded as %40."""
    dsn = "postgresql://user:pw@abc@host:5432/db"
    result = sanitize_dsn(dsn)
    assert "%40" in result


def test_sanitize_dsn_encodes_percent_in_password() -> None:
    """Verify a % that starts no escape sequence is percent-encoded as %25."""
    dsn = "postgresql://user:pw%zzc@host:5432/db"
    result = sanitize_dsn(dsn)
    assert "%25" in result


def test_sanitize_dsn_keeps_encoded_password_unchanged() -> None:
    """Verify an already percent-encoded password is not encoded twice."""
    dsn = "postgresql://user:pw%23abc%40@host:5432/db"
    assert sanitize_dsn(dsn) == dsn


def test_sanitize_dsn_unmatched_format_returns_asis() -> None:
    """Verify a DSN that doesn't match the pattern is returned unchanged."""
    assert sanitize_dsn("not-a-valid-dsn") == "not-a-valid-dsn"
    assert sanitize_dsn("") == ""


@pytest.mark.asyncio
async def test_connect_creates_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Database.connect creates an asyncpg pool."""
    mock_pool = create_autospec(asyncpg.Pool, instance=True)
    create_pool = AsyncMock(return_value=mock_pool)
    monkeypatch.setattr(asyncpg, "create_pool", create_pool)

    db = Database(_TEST_SETTINGS)
    await db.connect()

    create_pool.assert_awaited_once()
    assert db.pool is mock_pool


@pytest.mark.asyncio
async def test_disconnect_closes_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Database.disconnect closes the connection pool."""
    mock_pool = create_autospec(asyncpg.Pool, instance=True)
    create_pool = AsyncMock(return_value=mock_pool)
    monkeypatch.setattr(asyncpg, "create_pool", create_pool)

    db = Database(_TEST_SETTINGS)
    await db.connect()
    await db.disconnect()

    mock_pool.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_when_not_connected() -> None:
    """Verify disconnect is safe to call when never connected."""
    db = Database(_TEST_SETTINGS)
    await db.disconnect()


def test_pool_before_connect_raises() -> None:
    """Verify accessing pool before connect raises RuntimeError."""
    db = Database(_TEST_SETTINGS)
    with pytest.raises(RuntimeError, match="Database not connected"):
        _ = db.pool


def test_constructor_sanitizes_dsn() -> None:
    """Verify the constructor sanitizes the DSN upfront."""
    dsn = "postgresql://user:pw#abc@host:5432/db"
    db = Database(
        Settings(database_url=dsn, tmdb_api_key="tmdb-key", schema="marquise")
    )
    assert db._dsn != dsn
    assert "%23" in db._dsn


@pytest.mark.asyncio
async def test_ping_before_connect_returns_false() -> None:
    """Verify ping returns False when the pool was never opened."""
    db = Database(_TEST_SETTINGS)
    assert await db.ping() is False


@pytest.mark.asyncio
async def test_ping_returns_true_when_query_succeeds() -> None:
    """Verify ping returns True when a trivial query succeeds."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1)

    @asynccontextmanager
    async def acquire() -> AsyncIterator[AsyncMock]:
        yield conn

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(side_effect=acquire)

    db = Database(_TEST_SETTINGS)
    db._pool = mock_pool

    assert await db.ping() is True
    conn.fetchval.assert_awaited_once_with("SELECT 1")


@pytest.mark.asyncio
async def test_ping_returns_false_when_query_raises() -> None:
    """Verify ping returns False when the connection/query fails."""

    @asynccontextmanager
    async def acquire() -> AsyncIterator[AsyncMock]:
        raise asyncpg.PostgresError("connection lost")
        yield  # pragma: no cover - unreachable, satisfies generator shape

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(side_effect=acquire)

    db = Database(_TEST_SETTINGS)
    db._pool = mock_pool

    assert await db.ping() is False
