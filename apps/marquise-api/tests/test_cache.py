"""Tests for bounded API response cache."""

from __future__ import annotations

import pytest

from marquise_api.cache import BoundedInMemoryBackend


@pytest.mark.asyncio
async def test_cache_evicts_least_recently_used_entry() -> None:
    """Adding beyond capacity removes least-recently-used entry."""
    backend = BoundedInMemoryBackend(max_entries=2)
    await backend.set("first", b"1", expire=60)
    await backend.set("second", b"2", expire=60)
    await backend.get("first")

    await backend.set("third", b"3", expire=60)

    assert await backend.get("first") == b"1"
    assert await backend.get("second") is None
    assert await backend.get("third") == b"3"


@pytest.mark.asyncio
async def test_cache_removes_expired_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expired entries are unavailable and reclaimed before eviction."""
    now = 100
    monkeypatch.setattr("marquise_api.cache.time.time", lambda: now)
    backend = BoundedInMemoryBackend(max_entries=1)
    await backend.set("expired", b"old", expire=1)
    now = 102

    await backend.set("fresh", b"new", expire=60)

    assert await backend.get("expired") is None
    assert await backend.get("fresh") == b"new"


def test_cache_rejects_non_positive_capacity() -> None:
    """Backend rejects a capacity that cannot store responses."""
    with pytest.raises(ValueError, match="max_entries must be positive"):
        BoundedInMemoryBackend(max_entries=0)
