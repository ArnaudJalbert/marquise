"""Technology-agnostic transaction interface for audited screening writes."""

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from marquise.application.repositories import MovieRepository, ScreeningRepository
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.domain.value_objects.screening_audit import ScreeningAuditRecord


@dataclass(frozen=True, slots=True)
class ScreeningWriteResult:
    """Persisted success independent of HTTP status codes or response headers."""

    screening_id: str
    changed: bool
    screening: CreateScreeningUseCase.OutputData | None = None


@dataclass(frozen=True, slots=True)
class ScreeningReplay:
    """Validated request fingerprint and its committed result."""

    fingerprint: str
    result: ScreeningWriteResult


class ScreeningWriteSession(ABC):
    """Transaction-scoped collaborators plus audit and replay persistence."""

    create: CreateScreeningUseCase
    update: UpdateScreeningUseCase
    delete: DeleteScreeningUseCase
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


class ScreeningWriteTransaction(ABC):
    """Exclusive account/key transaction with bounded duplicate-request waiting."""

    @abstractmethod
    def open(
        self, account: str, key: str
    ) -> AbstractAsyncContextManager[ScreeningWriteSession]:
        """Open an atomic write, serializing requests sharing this account/key."""
