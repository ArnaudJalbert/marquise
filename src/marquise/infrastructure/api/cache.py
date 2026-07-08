"""In-memory TTL cache for the read-only API.

The underlying data only changes once a day (the nightly ``marquise import
all`` run), so short-lived in-process caching meaningfully cuts database load
without risking noticeably stale responses.
"""

from __future__ import annotations

import time
from collections.abc import Hashable

#: Default time-to-live for cached responses, in seconds. The database is
#: only refreshed once a day, so an hour keeps responses fresh while still
#: absorbing the vast majority of repeat traffic between refreshes.
DEFAULT_TTL_SECONDS = 3600.0


class TTLCache:
    """A minimal in-memory cache where entries expire after a fixed TTL.

    A single instance is shared across endpoints returning different response
    types, so values are stored and returned as ``object`` — callers are
    expected to ``cast`` the result back to the type they stored.
    """

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: How long an entry stays valid after being set.
        """
        self._ttl_seconds = ttl_seconds
        self._store: dict[Hashable, tuple[float, object]] = {}

    def get(self, key: Hashable) -> object | None:
        """Return the cached value for ``key``, or ``None`` if absent/expired.

        Args:
            key: The cache key.

        Returns:
            The cached value, or ``None`` on a miss.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: Hashable, value: object) -> None:
        """Store ``value`` under ``key`` for the configured TTL.

        Args:
            key: The cache key.
            value: The value to cache.
        """
        self._store[key] = (time.monotonic() + self._ttl_seconds, value)
