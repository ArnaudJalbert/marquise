"""Query use case: resolve a cinema's source and fetch its raw showtimes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    SourceRegistryQuery,
)
from marquise.domain.value_objects import CinemaId


class FetchShowtimesFromSourceQuery:
    """Resolve a cinema and its assigned source, then fetch raw showtimes."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching showtimes.

        Attributes:
            cinema_id: The ID of the cinema to fetch showtimes for.
            start_date: Earliest date to fetch (inclusive).
            end_date: Latest date to fetch (inclusive).
        """

        cinema_id: str
        start_date: date
        end_date: date

        def __post_init__(self) -> None:
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if self.start_date > self.end_date:
                raise ValueError("start_date must not be after end_date")

    @dataclass(frozen=True, slots=True)
    class ShowtimeDto:
        """A single showtime row returned by a source.

        Attributes:
            movie_title: The title of the movie.
            showtime: The showtime as a timezone-aware datetime.
            identifier: Source-specific identifier for fetching movie details.
            external_id: Source-native deduplication key.
            ticket_url: Direct link to purchase tickets.
            room: Room or auditorium name.
            language: Language or subtitle version.
        """

        movie_title: str
        showtime: datetime
        identifier: str | None = None
        external_id: str | None = None
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

        def __post_init__(self) -> None:
            if not self.movie_title.strip():
                raise ValueError("movie_title must not be empty")
            if self.showtime.tzinfo is None:
                raise ValueError("showtime must be timezone-aware")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned by this query.

        Attributes:
            cinema_id: The ID of the resolved cinema.
            cinema_name: The display name of the resolved cinema.
            source_name: The name of the source assigned to the cinema.
            rows: The raw showtime rows fetched from the source.
        """

        cinema_id: str
        cinema_name: str
        source_name: str
        rows: tuple[FetchShowtimesFromSourceQuery.ShowtimeDto, ...]

    def __init__(
        self,
        cinema_repository: CinemaRepository,
        assignment_repository: CinemaSourceAssignmentRepository,
        source_registry: SourceRegistryQuery,
    ) -> None:
        self.cinema_repository = cinema_repository
        self.assignment_repository = assignment_repository
        self.source_registry = source_registry

    async def execute(self, request: InputData) -> OutputData:
        """Resolve the cinema/source and fetch its showtimes.

        Args:
            request: Input data specifying the cinema and date range.

        Returns:
            Output data with the resolved cinema, source, and raw rows.

        Raises:
            CinemaNotFoundError: If the cinema does not exist.
            CinemaSourceAssignmentNotFoundError: If no source is assigned.
        """
        cinema_id = CinemaId(value=request.cinema_id)
        cinema = await self.cinema_repository.find_by_id(cinema_id)
        if cinema is None:
            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )

        assignment = await self.assignment_repository.find_by_cinema_id(cinema_id)
        if assignment is None:
            raise CinemaSourceAssignmentNotFoundError(
                f"No source assigned to cinema '{request.cinema_id}'"
            )

        start_dt = datetime.combine(request.start_date, datetime.min.time()).replace(
            tzinfo=UTC
        )
        end_dt = datetime.combine(request.end_date, datetime.max.time()).replace(
            tzinfo=UTC
        )

        rows = await self.source_registry.fetch_showtimes(
            cinema=cinema,
            source_definition=assignment.source,
            start_date=start_dt,
            end_date=end_dt,
        )

        return self.OutputData(
            cinema_id=str(cinema.id),
            cinema_name=cinema.name,
            source_name=str(assignment.source.name),
            rows=tuple(
                self.ShowtimeDto(
                    movie_title=r.movie_title,
                    showtime=r.showtime,
                    identifier=r.identifier,
                    external_id=r.external_id,
                    ticket_url=r.ticket_url,
                    room=r.room,
                    language=r.language,
                )
                for r in rows
            ),
        )
