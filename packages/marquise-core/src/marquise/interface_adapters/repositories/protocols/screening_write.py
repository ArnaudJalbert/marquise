"""Plain-data gateway for one audited write transaction."""

from typing import Protocol


class ScreeningWriteGateway(Protocol):
    """Audit/replay persistence and locking on a transaction-scoped connection."""

    async def lock_target(self, screening_id: str, *, lock_movie: bool) -> None:
        """Lock persisted state before the application captures it."""
        ...

    async def find_replay(self) -> dict | None:
        """Return the committed fingerprint/result for this account/key."""
        ...

    async def save_audit(self, record: dict) -> None:
        """Persist selected application-constructed audit fields."""
        ...

    async def save_replay(self, replay: dict) -> None:
        """Persist the fingerprint and technology-independent result."""
        ...
