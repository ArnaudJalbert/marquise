"""Find screening data problems and correct four non-identity fields."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.readers import ScreeningReader
from marquise.application.repositories import ScreeningRepository
from marquise.domain.value_objects import ScreeningId


class ScreeningDataAuditQuery:
    """Report duplicate identities, past showtimes, and blank screening text.

    A duplicate has the same cinema ID, movie ID, and showtime as an earlier
    row. Checked text means ticket URL, movie ID, cinema ID, and movie title.
    Timestamp provenance is not checked because the schema stores timestamps
    without timezone data and the reader returns every timestamp as UTC.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Optional cinema and time filters; no filters select every screening."""

        cinema_id: str | None = None
        start_date: datetime | None = None
        end_date: datetime | None = None

    @dataclass(frozen=True, slots=True)
    class Finding:
        """The failed check, screening ID, and reason it failed."""

        code: str
        screening_id: str
        detail: str

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """The number of rows read and every failed check found in those rows."""

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
        """Read matching screenings and return findings without writing any rows."""
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
    """Preview or update external ID, ticket URL, room, and language by screening ID."""

    @dataclass(frozen=True, slots=True)
    class Correction:
        """Editable values; None keeps the old value and an empty string replaces it."""

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
        """Corrections to preview, or one correction to apply with RECONCILE."""

        corrections: tuple[ReconcileScreeningsCommand.Correction, ...]
        apply: bool = False
        confirmation: str | None = None

    @dataclass(frozen=True, slots=True)
    class ItemResult:
        """A dry-run, updated, or not-found result for one screening ID."""

        screening_id: str
        status: str
        detail: str

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """One result per correction and the number of screenings updated."""

        items: tuple[ReconcileScreeningsCommand.ItemResult, ...]
        changed_count: int

    def __init__(self, screening_repository: ScreeningRepository) -> None:
        self._repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """Preview corrections, or update one when apply and RECONCILE are supplied."""
        if request.apply and request.confirmation != "RECONCILE":
            raise ValueError("confirmation must be RECONCILE when apply is enabled")
        if request.apply and len(request.corrections) != 1:
            raise ValueError("apply mode requires exactly one correction")
        results: list[ReconcileScreeningsCommand.ItemResult] = []
        changed = 0
        for correction in request.corrections:
            try:
                screening = await self._repository.find_by_id(
                    ScreeningId(value=correction.screening_id)
                )
            except ScreeningNotFoundError:
                results.append(
                    self.ItemResult(
                        correction.screening_id,
                        "not-found",
                        "screening was not found",
                    )
                )
                continue
            if request.apply:
                if correction.external_id is not None:
                    screening.external_id = correction.external_id
                if correction.ticket_url is not None:
                    screening.ticket_url = correction.ticket_url
                if correction.room is not None:
                    screening.room = correction.room
                if correction.language is not None:
                    screening.language = correction.language
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
