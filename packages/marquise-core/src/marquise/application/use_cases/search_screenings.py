"""Search screenings across all cinemas query (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
    ScreeningSummary,
)
from marquise.domain.value_objects import CinemaId, MovieId


class SearchScreeningsQuery:
    """Query for searching screenings by any combination of filters.

    Mirrors ``FetchScreeningsFromSourceQuery``: repositories return a light
    ``ScreeningSummary`` projection, so no full ``Screening``/``Movie``/
    ``Cinema`` entities are constructed per row.
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
    class OutputData:
        """Output data containing the matching screenings.

        Attributes:
            screenings: The matching page of screenings, ordered by showtime.
            total: Total number of screenings matching the filters, ignoring
                limit/offset.
        """

        screenings: tuple[ScreeningSummary, ...]
        total: int

    def __init__(
        self,
        screening_repository: ScreeningRepository,
        cinema_repository: CinemaRepository,
        movie_repository: MovieRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            screening_repository: A repository for querying screenings.
            cinema_repository: A repository for validating cinema_id filters.
            movie_repository: A repository for validating movie_id filters.
        """
        self.screening_repository = screening_repository
        self.cinema_repository = cinema_repository
        self.movie_repository = movie_repository

    async def execute(self, request: InputData) -> OutputData:
        """Search screenings by any combination of filters.

        Args:
            request: The input data with optional filters and pagination
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
            request.movie_id is not None
            and not await self.movie_repository.exists_by_id(
                MovieId(value=request.movie_id)
            )
        ):
            raise MovieNotFoundError(
                f"A movie with ID '{request.movie_id}' was not found"
            )
        if (
            request.cinema_id is not None
            and not await self.cinema_repository.exists_by_id(
                CinemaId(value=request.cinema_id)
            )
        ):
            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )

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

        screening_data = tuple(page.items)

        return self.OutputData(screenings=screening_data, total=page.total)
