"""Search screenings across all cinemas use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.repositories import ScreeningRepository
from marquise.domain.value_objects import CinemaId, MovieId


class SearchScreeningsUseCase:
    """Use case for searching screenings by any combination of filters."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for searching screenings.

        Attributes:
            movie: Optional movie title substring filter (case-insensitive).
            movie_id: Optional exact movie ID filter.
            cinema_id: Optional exact cinema ID filter.
            start_date: Optional start of the showtime range (inclusive).
            end_date: Optional end of the showtime range (inclusive).
            language: Optional exact language/subtitle version filter.
            page: Page number (1-based). Ignored when size is None.
            size: Max number of items per page. If None, all matching
                screenings are returned unbounded (page is ignored).
        """

        movie: str | None = None
        movie_id: str | None = None
        cinema_id: str | None = None
        start_date: datetime | None = None
        end_date: datetime | None = None
        language: str | None = None
        page: int = 1
        size: int | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If any provided string filter is empty or
                    whitespace-only, if the date range is inverted, if size
                    is provided but not positive, or if page is less than 1.
            """
            if self.movie is not None and not self.movie.strip():
                raise ValueError("movie must not be empty when provided")
            if self.movie_id is not None and not self.movie_id.strip():
                raise ValueError("movie_id must not be empty when provided")
            if self.cinema_id is not None and not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty when provided")
            if self.language is not None and not self.language.strip():
                raise ValueError("language must not be empty when provided")
            if (
                self.start_date is not None
                and self.end_date is not None
                and self.start_date > self.end_date
            ):
                raise ValueError("start_date must not be after end_date")
            if self.size is not None and self.size < 1:
                raise ValueError("size must be positive when provided")
            if self.page < 1:
                raise ValueError("page must be at least 1")

    @dataclass(frozen=True, slots=True)
    class ScreeningData:
        """A single screening in the output.

        Attributes:
            id: Unique identifier of the screening.
            movie_id: The screened movie's ID.
            movie_title: The screened movie's title.
            cinema_id: The hosting cinema's ID.
            cinema_name: The hosting cinema's display name.
            showtime: The screening time in ISO 8601 format.
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).
        """

        id: str
        movie_id: str
        movie_title: str
        cinema_id: str
        cinema_name: str
        showtime: str
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the matching screenings.

        Attributes:
            screenings: The matching page of screenings, ordered by showtime.
            total: Total number of screenings matching the filters, ignoring
                limit/offset.
        """

        screenings: tuple[SearchScreeningsUseCase.ScreeningData, ...]
        total: int

    def __init__(self, screening_repository: ScreeningRepository) -> None:
        """Initialize the use case.

        Args:
            screening_repository: A repository for querying screenings.
        """
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """Search screenings by any combination of filters.

        Args:
            request: The input data with optional filters and pagination
                parameters.

        Returns:
            The output data with the matching page of screenings and the
            total count.
        """
        if request.size is not None:
            limit = request.size
            offset = (request.page - 1) * request.size
        else:
            limit = None
            offset = 0

        page = await self.screening_repository.search(
            movie_id=MovieId(value=request.movie_id)
            if request.movie_id is not None
            else None,
            movie_title=request.movie,
            cinema_id=CinemaId(value=request.cinema_id)
            if request.cinema_id is not None
            else None,
            start_date=request.start_date,
            end_date=request.end_date,
            language=request.language,
            limit=limit,
            offset=offset,
        )

        screening_data = tuple(
            self.ScreeningData(
                id=str(s.id),
                movie_id=str(s.movie.id),
                movie_title=s.movie.title,
                cinema_id=str(s.cinema.id),
                cinema_name=s.cinema.name,
                showtime=s.showtime.value.isoformat(),
                ticket_url=s.ticket_url,
                room=s.room,
                language=s.language,
            )
            for s in page.items
        )

        return self.OutputData(screenings=screening_data, total=page.total)
