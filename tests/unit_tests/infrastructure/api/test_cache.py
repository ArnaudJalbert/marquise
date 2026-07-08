"""Tests for the in-memory TTL cache used by the read-only API."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from marquise.infrastructure.api.cache import TTLCache, cached


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


@pytest.mark.asyncio
async def test_cached_decorator_invokes_the_function_once_for_the_same_key() -> None:
    """A second call with identical key_params reuses the cached result."""
    call_count = 0

    @cached("greeting", key_params=("name",))
    async def greet(name: str, cache: TTLCache) -> str:
        nonlocal call_count
        call_count += 1
        return f"hello {name}"

    cache = TTLCache(ttl_seconds=60)

    first = await greet(name="Ada", cache=cache)
    second = await greet(name="Ada", cache=cache)

    assert first == "hello Ada"
    assert second == "hello Ada"
    assert call_count == 1


@pytest.mark.asyncio
async def test_cached_decorator_treats_different_key_params_separately() -> None:
    """Different key_params values produce independent cache entries."""
    call_count = 0

    @cached("greeting", key_params=("name",))
    async def greet(name: str, cache: TTLCache) -> str:
        nonlocal call_count
        call_count += 1
        return f"hello {name}"

    cache = TTLCache(ttl_seconds=60)

    await greet(name="Ada", cache=cache)
    await greet(name="Grace", cache=cache)

    assert call_count == 2


@pytest.mark.asyncio
async def test_cached_decorator_does_not_cache_a_raised_exception() -> None:
    """A failed call is not cached, so a retry re-invokes the function."""
    call_count = 0

    @cached("boom", key_params=())
    async def fail(cache: TTLCache) -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("nope")

    cache = TTLCache(ttl_seconds=60)

    with pytest.raises(ValueError, match="nope"):
        await fail(cache=cache)
    with pytest.raises(ValueError, match="nope"):
        await fail(cache=cache)

    assert call_count == 2
