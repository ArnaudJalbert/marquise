"""Audit policy and retry-safe orchestration for authenticated screening writes."""

from __future__ import annotations

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
from marquise.application.use_cases._screening_helpers import (
    UNSET,
    _Unset,
    is_provided,
    reject_blank_when_provided,
    require_non_empty,
    require_timezone_aware_showtime,
)
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.domain.value_objects import ScreeningId
from marquise.domain.value_objects.screening_audit import (
    MovieSnapshot,
    ScreeningAuditRecord,
    ScreeningSnapshot,
)


class WriteScreeningUseCase:
    """Commit screening mutation, application-built history, and replay together.

    The existing dedicated mutation use cases remain injectable collaborators
    scoped to the same transaction. No persistence technology or HTTP types
    enter this orchestration.
    """

    @dataclass(frozen=True, slots=True)
    class Context:
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
                or any(
                    unicodedata.category(char).startswith("C") for char in self.reason
                )
            ):
                raise ValueError("Invalid X-Change-Reason")

    @dataclass(frozen=True, slots=True)
    class CreateInput:
        """Validated screening creation payload owned by this command."""

        movie_id: str
        cinema_id: str
        showtime: datetime
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None
        external_id: str | None = None

        def __post_init__(self) -> None:
            """Validate required IDs, showtime, and optional metadata."""
            require_non_empty(self.movie_id, "movie_id")
            require_non_empty(self.cinema_id, "cinema_id")
            require_timezone_aware_showtime(self.showtime)
            reject_blank_when_provided(self.ticket_url, "ticket_url")
            reject_blank_when_provided(self.room, "room")
            reject_blank_when_provided(self.language, "language")
            reject_blank_when_provided(self.external_id, "external_id")

    @dataclass(frozen=True, slots=True)
    class UpdateInput:
        """Validated partial screening update payload owned by this command."""

        screening_id: str
        movie_id: str | _Unset = UNSET
        cinema_id: str | _Unset = UNSET
        showtime: datetime | _Unset = UNSET
        ticket_url: str | None | _Unset = UNSET
        room: str | None | _Unset = UNSET
        language: str | None | _Unset = UNSET
        external_id: str | None | _Unset = UNSET

        def __post_init__(self) -> None:
            """Validate the target and each explicitly provided field."""
            require_non_empty(self.screening_id, "screening_id")
            if is_provided(self.movie_id):
                require_non_empty(self.movie_id, "movie_id")
            if is_provided(self.cinema_id):
                require_non_empty(self.cinema_id, "cinema_id")
            if is_provided(self.showtime):
                require_timezone_aware_showtime(self.showtime)
            if is_provided(self.ticket_url):
                reject_blank_when_provided(self.ticket_url, "ticket_url")
            if is_provided(self.room):
                reject_blank_when_provided(self.room, "room")
            if is_provided(self.language):
                reject_blank_when_provided(self.language, "language")
            if is_provided(self.external_id):
                reject_blank_when_provided(self.external_id, "external_id")

    @dataclass(frozen=True, slots=True)
    class DeleteInput:
        """Validated screening deletion payload owned by this command."""

        screening_id: str

        def __post_init__(self) -> None:
            """Validate the screening ID."""
            require_non_empty(self.screening_id, "screening_id")

    MutationInput = CreateInput | UpdateInput | DeleteInput

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Validated command payload and attributable retry context."""

        context: WriteScreeningUseCase.Context
        mutation: WriteScreeningUseCase.MutationInput

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
            if isinstance(mutation, self.CreateInput)
            else "update"
            if isinstance(mutation, self.UpdateInput)
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
            if not isinstance(mutation, self.CreateInput):
                await session.lock_target(
                    mutation.screening_id, lock_movie=operation == "delete"
                )
                existing = await session.screenings.find_by_id(
                    ScreeningId(value=mutation.screening_id)
                )
                before = ScreeningSnapshot.from_screening(existing)

            if isinstance(mutation, self.CreateInput):
                created = await session.create.execute(
                    CreateScreeningUseCase.InputData(
                        movie_id=mutation.movie_id,
                        cinema_id=mutation.cinema_id,
                        showtime=mutation.showtime,
                        ticket_url=mutation.ticket_url,
                        room=mutation.room,
                        language=mutation.language,
                        external_id=mutation.external_id,
                    )
                )
                output = ScreeningWriteResult.Screening(**asdict(created))
                changed = True
                target = output.id
            elif isinstance(mutation, self.UpdateInput):
                updated = await session.update.execute(
                    UpdateScreeningUseCase.InputData(
                        screening_id=mutation.screening_id,
                        movie_id=mutation.movie_id,
                        cinema_id=mutation.cinema_id,
                        showtime=mutation.showtime,
                        ticket_url=mutation.ticket_url,
                        room=mutation.room,
                        language=mutation.language,
                        external_id=mutation.external_id,
                    )
                )
                output = ScreeningWriteResult.Screening(**asdict(updated))
                changed = any(name != "screening_id" for name in values)
                target = output.id
            else:
                movie = MovieSnapshot.from_movie(existing.movie)
                await session.delete.execute(
                    DeleteScreeningUseCase.InputData(screening_id=mutation.screening_id)
                )
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
