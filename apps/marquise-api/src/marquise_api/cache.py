"""Bounded in-memory backend for API response caching."""

from __future__ import annotations

import time
from asyncio import Lock
from collections import OrderedDict
from dataclasses import dataclass

from fastapi_cache.backends import Backend


@dataclass(frozen=True, slots=True)
class _Entry:
    data: bytes
    expires_at: int


class BoundedInMemoryBackend(Backend):
    """Store a fixed number of cached responses with TTL and LRU eviction."""

    def __init__(self, max_entries: int) -> None:
        """Initialize backend with a positive entry limit."""
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._store: OrderedDict[str, _Entry] = OrderedDict()
        self._lock = Lock()

    @property
    def _now(self) -> int:
        return int(time.time())

    def _get(self, key: str) -> _Entry | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._now:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return entry

    async def get_with_ttl(self, key: str) -> tuple[int, bytes | None]:
        """Return remaining TTL and cached bytes for key."""
        async with self._lock:
            entry = self._get(key)
            if entry is None:
                return 0, None
            return entry.expires_at - self._now, entry.data

    async def get(self, key: str) -> bytes | None:
        """Return cached bytes for key."""
        async with self._lock:
            entry = self._get(key)
            return entry.data if entry is not None else None

    async def set(self, key: str, value: bytes, expire: int | None = None) -> None:
        """Cache bytes and evict expired or least-recently-used entries."""
        async with self._lock:
            # ponytail: O(n) sweep bounded by max_entries; use heap if cap grows.
            for expired_key in [
                stored_key
                for stored_key, entry in self._store.items()
                if entry.expires_at <= self._now
            ]:
                del self._store[expired_key]
            self._store.pop(key, None)
            while len(self._store) >= self._max_entries:
                self._store.popitem(last=False)
            self._store[key] = _Entry(value, self._now + (expire or 0))

    async def clear(self, namespace: str | None = None, key: str | None = None) -> int:
        """Delete matching cached entries and return deletion count."""
        async with self._lock:
            if namespace is not None:
                keys = [key for key in self._store if key.startswith(namespace)]
            elif key is not None and key in self._store:
                keys = [key]
            else:
                keys = []
            for stored_key in keys:
                del self._store[stored_key]
            return len(keys)
