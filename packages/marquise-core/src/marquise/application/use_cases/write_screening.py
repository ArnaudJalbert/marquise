"""Audit policy and retry-safe orchestration for authenticated screening writes."""

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, replace
from datetime import UTC, datetime
from hashlib import sha256

from marquise.application.exceptions import ScreeningIdempotencyConflictError
from marquise.application.transactions.screening_write import (
    ScreeningReplay,
    ScreeningWriteResult,
    ScreeningWriteSession,
    ScreeningWriteTransaction,
)
from marquise.application.use_cases._screening_helpers import is_provided
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.domain.value_objects import ScreeningId
from marquise.domain.value_objects.screening_audit import (
    MovieSnapshot,
    ScreeningAuditRecord,
    ScreeningSnapshot,
)


@dataclass(frozen=True, slots=True)
class ScreeningWriteContext:
    """Verified account and validated client-supplied write intent."""

    account: str
    key: str
    reason: str

    def __post_init__(self) -> None:
        """Reject missing identity, malformed keys, and invalid reasons."""
        if not self.account.strip():
            raise ValueError("account must not be empty")
        if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", self.key) is None:
            raise ValueError("Invalid Idempotency-Key")
        if (
            not self.reason.strip()
            or len(self.reason) > 500
            or any(unicodedata.category(char).startswith("C") for char in self.reason)
        ):
            raise ValueError("Invalid X-Change-Reason")


class WriteScreeningUseCase:
    """Commit screening mutation, application-built history, and replay together.

    The existing dedicated mutation use cases remain injectable collaborators
    scoped to the same transaction. No persistence technology or HTTP types
    enter this orchestration.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Validated mutation and attributable retry context."""

        context: ScreeningWriteContext
        mutation: (
            CreateScreeningUseCase.InputData
            | UpdateScreeningUseCase.InputData
            | DeleteScreeningUseCase.InputData
        )

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Committed outcome; ``screening`` is ``None`` after deletion."""

        @dataclass(frozen=True, slots=True)
        class Screening:
            """Written screening values with parent display names."""

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

    class Session(ScreeningWriteSession):
        """Write session carrying the transaction-scoped mutation use cases."""

        create: CreateScreeningUseCase
        update: UpdateScreeningUseCase
        delete: DeleteScreeningUseCase

    def __init__(
        self,
        transaction: ScreeningWriteTransaction[Session],
        clock: Callable[[], datetime],
    ) -> None:
        """Inject transaction factory and timezone-aware clock."""
        self._transaction = transaction
        self._clock = clock

    async def execute(self, input_data: InputData) -> OutputData:
        """Perform one intended change or replay its original committed success."""
        mutation = input_data.mutation
        context = input_data.context
        operation = (
            "create"
            if isinstance(mutation, CreateScreeningUseCase.InputData)
            else "update"
            if isinstance(mutation, UpdateScreeningUseCase.InputData)
            else "delete"
        )
        values = {
            field.name: (
                value.astimezone(UTC).isoformat()
                if isinstance(value, datetime)
                else value
            )
            for field in fields(mutation)
            if is_provided(value := getattr(mutation, field.name))
        }
        fingerprint = sha256(
            json.dumps(
                {"operation": operation, "reason": context.reason, "values": values},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        async with self._transaction.open(context.account, context.key) as session:
            replay = await session.find_replay()
            if replay is not None:
                if replay.fingerprint != fingerprint:
                    raise ScreeningIdempotencyConflictError(
                        "Idempotency-Key already used for a different request"
                    )
                return self._output(replay.result)

            before = None
            removed_movie = None
            if not isinstance(mutation, CreateScreeningUseCase.InputData):
                await session.lock_target(
                    mutation.screening_id, lock_movie=operation == "delete"
                )
                existing = await session.screenings.find_by_id(
                    ScreeningId(value=mutation.screening_id)
                )
                before = ScreeningSnapshot.from_screening(existing)

            if isinstance(mutation, CreateScreeningUseCase.InputData):
                created = await session.create.execute(mutation)
                output = ScreeningWriteResult.Screening(**asdict(created))
                changed = True
                target = output.id
            elif isinstance(mutation, UpdateScreeningUseCase.InputData):
                updated = await session.update.execute(mutation)
                output = ScreeningWriteResult.Screening(**asdict(updated))
                changed = any(name != "screening_id" for name in values)
                target = output.id
            else:
                movie = MovieSnapshot.from_movie(existing.movie)
                await session.delete.execute(mutation)
                if await session.movies.find_by_id(existing.movie.id) is None:
                    removed_movie = movie
                output = None
                changed = True
                target = mutation.screening_id

            after = None
            if output is not None:
                persisted = await session.screenings.find_by_id(
                    ScreeningId(value=target)
                )
                after = ScreeningSnapshot.from_screening(persisted)
                output = replace(
                    output,
                    movie_title=persisted.movie.title,
                    cinema_name=persisted.cinema.name,
                )
            if changed:
                await session.save_audit(
                    ScreeningAuditRecord(
                        account=context.account,
                        key=context.key,
                        operation=operation,
                        target=target,
                        timestamp=self._clock(),
                        reason=context.reason,
                        before=before,
                        after=after,
                        removed_movie=removed_movie,
                    )
                )
            result = ScreeningWriteResult(
                screening_id=target, changed=changed, screening=output
            )
            await session.save_replay(
                ScreeningReplay(fingerprint=fingerprint, result=result)
            )
            return self._output(result)

    @classmethod
    def _output(cls, result: ScreeningWriteResult) -> OutputData:
        """Map the transaction's committed result into this command's output."""
        screening = result.screening
        return cls.OutputData(
            screening_id=result.screening_id,
            changed=result.changed,
            screening=None
            if screening is None
            else cls.OutputData.Screening(**asdict(screening)),
        )
