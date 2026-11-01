"""Technology-agnostic transaction interface for audited screening writes."""

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime

from marquise.application.repositories import MovieRepository, ScreeningRepository
from marquise.domain.value_objects.screening_audit import ScreeningAuditRecord


@dataclass(frozen=True, slots=True)
class ScreeningWriteResult:
    """Persisted success independent of HTTP status codes or response headers."""

    @dataclass(frozen=True, slots=True)
    class Screening:
        """Committed screening values with parent display names."""

        id: str
        movie_id: str
        movie_title: str
        cinema_id: str
        cinema_name: str
        showtime: datetime
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

    screening_id: str
    changed: bool
    screening: Screening | None = None


@dataclass(frozen=True, slots=True)
class ScreeningReplay:
    """Validated request fingerprint and its committed result."""

    fingerprint: str
    result: ScreeningWriteResult


class ScreeningWriteSession(ABC):
    """Transaction-scoped repositories plus audit and replay persistence.

    Consumers subclass this to declare the mutation collaborators they call.
    """

    screenings: ScreeningRepository
    movies: MovieRepository

    @abstractmethod
    async def lock_target(self, screening_id: str, *, lock_movie: bool) -> None:
        """Protect before-state and, for deletion, movie metadata until commit."""

    @abstractmethod
    async def find_replay(self) -> ScreeningReplay | None:
        """Return this account/key's committed result, if any."""

    @abstractmethod
    async def save_audit(self, record: ScreeningAuditRecord) -> None:
        """Save application-constructed history in the current transaction."""

    @abstractmethod
    async def save_replay(self, replay: ScreeningReplay) -> None:
        """Save a successful result in the current transaction."""


class ScreeningWriteTransaction[SessionT: ScreeningWriteSession](ABC):
    """Exclusive account/key transaction with bounded duplicate-request waiting."""

    @abstractmethod
    def open(self, account: str, key: str) -> AbstractAsyncContextManager[SessionT]:
        """Open an atomic write, serializing requests sharing this account/key."""
