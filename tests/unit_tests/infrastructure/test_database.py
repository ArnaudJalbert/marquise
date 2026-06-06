"""Unit tests for infrastructure database module."""

from __future__ import annotations

from unittest.mock import AsyncMock, create_autospec

import asyncpg
import pytest

from marquise.infrastructure.supabase.config import Settings
from marquise.infrastructure.supabase.database import Database, sanitize_dsn

_TEST_SETTINGS = Settings(
    database_url="postgresql://user:pass@localhost:5432/test",
    supabase_url="https://test.supabase.co",
    supabase_publishable_key="sb_publishable_test",
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
    """Verify a % in the password is percent-encoded as %25."""
    dsn = "postgresql://user:pw%abc@host:5432/db"
    result = sanitize_dsn(dsn)
    assert "%25" in result


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
        Settings(
            database_url=dsn,
            supabase_url="https://test.supabase.co",
            supabase_publishable_key="sb_publishable_test",
        )
    )
    assert db._dsn != dsn
    assert "%23" in db._dsn
