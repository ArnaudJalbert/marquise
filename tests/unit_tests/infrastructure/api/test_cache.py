"""Tests for the in-memory TTL cache used by the read-only API."""

from __future__ import annotations

from unittest.mock import patch

from marquise.infrastructure.api.cache import TTLCache


def test_get_returns_none_on_miss() -> None:
    """An unset key returns None."""
    cache: TTLCache = TTLCache(ttl_seconds=60)
    assert cache.get("missing") is None


def test_set_then_get_returns_the_cached_value() -> None:
    """A value set under a key is returned by a subsequent get."""
    cache: TTLCache = TTLCache(ttl_seconds=60)
    cache.set("key", {"a": 1})
    assert cache.get("key") == {"a": 1}


def test_entry_expires_after_ttl() -> None:
    """An entry is no longer returned once the TTL has elapsed."""
    with patch("marquise.infrastructure.api.cache.time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = 0.0
        cache: TTLCache = TTLCache(ttl_seconds=10)
        cache.set("key", "value")

        mock_monotonic.return_value = 5.0
        assert cache.get("key") == "value"

        mock_monotonic.return_value = 10.0
        assert cache.get("key") is None


def test_expired_entry_is_evicted_from_the_store() -> None:
    """Reading an expired entry removes it from the internal store."""
    with patch("marquise.infrastructure.api.cache.time.monotonic") as mock_monotonic:
        mock_monotonic.return_value = 0.0
        cache: TTLCache = TTLCache(ttl_seconds=10)
        cache.set("key", "value")

        mock_monotonic.return_value = 20.0
        cache.get("key")

        assert "key" not in cache._store
