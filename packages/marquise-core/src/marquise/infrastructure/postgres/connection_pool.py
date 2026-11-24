"""Connection acquisition shared by pooled and transaction-scoped gateways."""

from contextlib import AbstractAsyncContextManager
from typing import Protocol

import asyncpg


class ConnectionPool(Protocol):
    """The connection acquisition interface used by SQL gateways."""

    def acquire(self) -> AbstractAsyncContextManager[asyncpg.Connection]:
        """Acquire a connection without deciding transaction ownership."""
        ...
