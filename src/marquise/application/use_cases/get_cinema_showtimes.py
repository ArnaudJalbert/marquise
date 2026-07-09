"""Get a cinema's showtimes within a date range use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import CinemaRepository, ScreeningRepository
from marquise.domain.value_objects import CinemaId


class GetCinemaShowtimesUseCase:
    """Use case for listing a cinema's screenings within a date range."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching a cinema's showtimes.

        Attributes:
            cinema_id: The cinema to fetch showtimes for.
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).
        """

        cinema_id: str
        start_date: datetime
        end_date: datetime

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If cinema_id is empty or the range is inverted.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            # Comparing an aware and a naive datetime raises TypeError, not
            # ValueError, so normalize local copies for the comparison only
            # (naive values are assumed UTC, matching the rest of the
            # persistence layer) rather than letting mixed inputs crash.
            start = self.start_date.replace(tzinfo=self.start_date.tzinfo or UTC)
            end = self.end_date.replace(tzinfo=self.end_date.tzinfo or UTC)
            if start > end:
                raise ValueError("start_date must not be after end_date")

    @dataclass(frozen=True, slots=True)
    class ScreeningData:
        """A single screening in the output.

        Attributes:
            id: Unique identifier of the screening.
            movie_id: The screened movie's ID.
            movie_title: The screened movie's title.
            showtime: The screening time in ISO 8601 format.
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).
        """

        id: str
        movie_id: str
        movie_title: str
        showtime: str
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the cinema's screenings.

        Attributes:
            cinema_id: The cinema's ID.
            cinema_name: The cinema's display name.
            screenings: The matching screenings, ordered by showtime.
        """

        cinema_id: str
        cinema_name: str
        screenings: tuple[GetCinemaShowtimesUseCase.ScreeningData, ...]

    def __init__(
        self,
        cinema_repository: CinemaRepository,
        screening_repository: ScreeningRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: A repository for querying cinemas.
            screening_repository: A repository for querying screenings.
        """
        self.cinema_repository = cinema_repository
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """List a cinema's screenings within the requested date range.

        Args:
            request: The input data with cinema ID and date range.

        Returns:
            The output data with the cinema and its screenings.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        cinema_id = CinemaId(value=request.cinema_id)
        cinema = await self.cinema_repository.find_by_id(cinema_id)
        if cinema is None:
            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )

        screenings = await self.screening_repository.find_by_cinema_and_date_range(
            cinema_id=cinema_id,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        screening_data = tuple(
            self.ScreeningData(
                id=str(s.id),
                movie_id=str(s.movie.id),
                movie_title=s.movie.title,
                showtime=s.showtime.value.isoformat(),
                ticket_url=s.ticket_url,
                room=s.room,
                language=s.language,
            )
            for s in screenings
        )

        return self.OutputData(
            cinema_id=str(cinema.id),
            cinema_name=cinema.name,
            screenings=screening_data,
        )
