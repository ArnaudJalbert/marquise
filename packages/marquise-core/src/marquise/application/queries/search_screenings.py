"""Search screenings across all cinemas query (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.application.readers import ScreeningReader
from marquise.application.repositories import CinemaRepository, MovieRepository
from marquise.application.repositories.page import page_window
from marquise.domain.value_objects import CinemaId, MovieId


class SearchScreeningsQuery:
    """Query for searching screenings by any combination of filters.

    Uses a dedicated reader projection, so no domain entities are constructed
    per result row.
    """

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
        """Display data for one screening search result."""

        id: str
        movie_id: str
        movie_title: str
        cinema_id: str
        cinema_name: str
        showtime: datetime
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

        screenings: tuple[SearchScreeningsQuery.ScreeningData, ...]
        total: int

    def __init__(
        self,
        screening_reader: ScreeningReader,
        cinema_repository: CinemaRepository,
        movie_repository: MovieRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            screening_reader: A reader for screening display data.
            cinema_repository: A repository for validating cinema_id filters.
            movie_repository: A repository for validating movie_id filters.
        """
        self.screening_reader = screening_reader
        self.cinema_repository = cinema_repository
        self.movie_repository = movie_repository

    async def execute(self, input_data: InputData) -> OutputData:
        """Search screenings by any combination of filters.

        Args:
            input_data: The input data with optional filters and pagination
                parameters.

        Returns:
            The output data with the matching page of screenings and the
            total count.

        Raises:
            MovieNotFoundError: If movie_id is provided but no movie with
                that ID exists.
            CinemaNotFoundError: If cinema_id is provided but no cinema with
                that ID exists.
        """
        if (
            input_data.movie_id is not None
            and not await self.movie_repository.exists_by_id(
                MovieId(value=input_data.movie_id)
            )
        ):
            raise MovieNotFoundError(
                f"A movie with ID '{input_data.movie_id}' was not found"
            )
        if (
            input_data.cinema_id is not None
            and not await self.cinema_repository.exists_by_id(
                CinemaId(value=input_data.cinema_id)
            )
        ):
            raise CinemaNotFoundError(
                f"A cinema with ID '{input_data.cinema_id}' was not found"
            )

        limit, offset = (
            (None, 0)
            if input_data.size is None
            else page_window(input_data.page, input_data.size)
        )

        page = await self.screening_reader.search(
            movie_id=input_data.movie_id,
            movie_title=input_data.movie,
            cinema_id=input_data.cinema_id,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
            language=input_data.language,
            limit=limit,
            offset=offset,
        )

        return self.OutputData(
            screenings=tuple(
                self.ScreeningData(
                    id=screening.id,
                    movie_id=screening.movie_id,
                    movie_title=screening.movie_title,
                    cinema_id=screening.cinema_id,
                    cinema_name=screening.cinema_name,
                    showtime=screening.showtime,
                    ticket_url=screening.ticket_url,
                    room=screening.room,
                    language=screening.language,
                )
                for screening in page.items
            ),
            total=page.total,
        )
