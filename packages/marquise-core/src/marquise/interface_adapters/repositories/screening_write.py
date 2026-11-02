"""Map immutable application/domain history through an injected data gateway."""

from dataclasses import asdict
from datetime import datetime

from marquise.application.repositories import MovieRepository, ScreeningRepository
from marquise.application.transactions.screening_write import (
    ScreeningReplay,
    ScreeningWriteResult,
)
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.application.use_cases.write_screening import WriteScreeningUseCase
from marquise.domain.value_objects.screening_audit import ScreeningAuditRecord
from marquise.interface_adapters.repositories.protocols.screening_write import (
    ScreeningWriteGateway,
)


class ScreeningWriteSessionAdapter(WriteScreeningUseCase.Session):
    """Injected transaction-scoped collaborators, with DTO persistence mapping."""

    def __init__(
        self,
        gateway: ScreeningWriteGateway,
        *,
        create: CreateScreeningUseCase,
        update: UpdateScreeningUseCase,
        delete: DeleteScreeningUseCase,
        screenings: ScreeningRepository,
        movies: MovieRepository,
    ) -> None:
        """Accept collaborators built by the infrastructure composition root."""
        self._gateway = gateway
        self.create = create
        self.update = update
        self.delete = delete
        self.screenings = screenings
        self.movies = movies

    async def lock_target(self, screening_id: str, *, lock_movie: bool) -> None:
        """Delegate state protection without database dependencies."""
        await self._gateway.lock_target(screening_id, lock_movie=lock_movie)

    async def find_replay(self) -> ScreeningReplay | None:
        """Map persisted result data without reading potentially deleted entities."""
        data = await self._gateway.find_replay()
        if data is None:
            return None
        result = dict(data["result"])
        screening = result["screening"]
        if screening is not None:
            screening = dict(screening)
            screening["showtime"] = datetime.fromisoformat(screening["showtime"])
            result["screening"] = ScreeningWriteResult.Screening(**screening)
        return ScreeningReplay(
            fingerprint=data["fingerprint"], result=ScreeningWriteResult(**result)
        )

    async def save_audit(self, record: ScreeningAuditRecord) -> None:
        """Map the use-case-built immutable record to plain data."""
        await self._gateway.save_audit(asdict(record))

    async def save_replay(self, replay: ScreeningReplay) -> None:
        """Map a committed success candidate to plain persistence data."""
        await self._gateway.save_replay(asdict(replay))
