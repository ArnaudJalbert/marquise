"""Application-level showtime auditing and guarded reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from marquise.application.readers import ScreeningReader
from marquise.application.repositories import ScreeningRepository
from marquise.domain.value_objects import ScreeningId


class ScreeningDataAuditQuery:
    """Inspect screening projections for actionable reliability findings."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Audit filters. An empty request audits the complete projection."""

        cinema_id: str | None = None
        start_date: datetime | None = None
        end_date: datetime | None = None

    @dataclass(frozen=True, slots=True)
    class Finding:
        """One deterministic data-quality finding."""

        code: str
        screening_id: str
        detail: str

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Audit findings and the number of inspected rows."""

        inspected_count: int
        findings: tuple[ScreeningDataAuditQuery.Finding, ...]

    def __init__(
        self,
        screening_reader: ScreeningReader,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._reader = screening_reader
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(self, request: InputData) -> OutputData:
        """Inspect rows without calling a write port."""
        page = await self._reader.search(
            cinema_id=request.cinema_id,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=None,
            offset=0,
        )
        findings: list[ScreeningDataAuditQuery.Finding] = []
        identities: dict[tuple[str, str, datetime], str] = {}
        now = self._clock()
        for row in page.items:
            identity = (row.cinema_id, row.movie_id, row.showtime)
            previous = identities.get(identity)
            if previous is not None:
                findings.append(
                    self.Finding(
                        "duplicate_identity",
                        row.id,
                        f"duplicates screening {previous} on the same "
                        "cinema/movie/showtime",
                    )
                )
            else:
                identities[identity] = row.id
            if row.showtime < now:
                findings.append(
                    self.Finding(
                        "stale_showtime",
                        row.id,
                        "showtime is before the audit clock",
                    )
                )
            if not row.ticket_url or not row.ticket_url.strip():
                findings.append(
                    self.Finding(
                        "missing_ticket_url",
                        row.id,
                        "ticket URL is empty",
                    )
                )
            if row.showtime.tzinfo is None:
                findings.append(
                    self.Finding(
                        "naive_showtime",
                        row.id,
                        "showtime has no timezone",
                    )
                )
            elif row.showtime.utcoffset() != timedelta(0):
                findings.append(
                    self.Finding(
                        "non_utc_showtime",
                        row.id,
                        "showtime is not represented in UTC",
                    )
                )
            if (
                not row.movie_id.strip()
                or not row.cinema_id.strip()
                or not row.movie_title.strip()
            ):
                findings.append(
                    self.Finding(
                        "malformed_identity",
                        row.id,
                        "movie/cinema identity or title is empty",
                    )
                )
        return self.OutputData(
            inspected_count=len(page.items), findings=tuple(findings)
        )


class ReconcileScreeningsCommand:
    """Preview or explicitly apply safe metadata corrections by screening ID."""

    @dataclass(frozen=True, slots=True)
    class Correction:
        """Allowed non-identity fields to correct."""

        screening_id: str
        external_id: str | None = None
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

        def __post_init__(self) -> None:
            if not self.screening_id.strip():
                raise ValueError("screening_id must not be empty")
            if not any(
                value is not None
                for value in (
                    self.external_id,
                    self.ticket_url,
                    self.room,
                    self.language,
                )
            ):
                raise ValueError("at least one correction field is required")

    @dataclass(frozen=True, slots=True)
    class InputData:
        corrections: tuple[ReconcileScreeningsCommand.Correction, ...]
        apply: bool = False
        confirmation: str | None = None

    @dataclass(frozen=True, slots=True)
    class ItemResult:
        screening_id: str
        status: str
        detail: str

    @dataclass(frozen=True, slots=True)
    class OutputData:
        items: tuple[ReconcileScreeningsCommand.ItemResult, ...]
        changed_count: int

    def __init__(self, screening_repository: ScreeningRepository) -> None:
        self._repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """Validate all corrections, then write only with two explicit guards."""
        if request.apply and request.confirmation != "RECONCILE":
            raise ValueError("confirmation must be RECONCILE when apply is enabled")
        results: list[ReconcileScreeningsCommand.ItemResult] = []
        changed = 0
        for correction in request.corrections:
            screening = await self._repository.find_by_id(
                ScreeningId(value=correction.screening_id)
            )
            if request.apply:
                screening.external_id = correction.external_id or screening.external_id
                screening.ticket_url = correction.ticket_url or screening.ticket_url
                screening.room = correction.room or screening.room
                screening.language = correction.language or screening.language
                updated = await self._repository.update(screening)
                if updated is None:
                    results.append(
                        self.ItemResult(
                            correction.screening_id,
                            "not-found",
                            "screening disappeared before update",
                        )
                    )
                    continue
                changed += 1
                results.append(
                    self.ItemResult(
                        correction.screening_id, "updated", "metadata updated"
                    )
                )
            else:
                results.append(
                    self.ItemResult(
                        correction.screening_id,
                        "dry-run",
                        "validated; no write performed",
                    )
                )
        return self.OutputData(items=tuple(results), changed_count=changed)
