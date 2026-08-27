"""Get all of a movie's screenings use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.repositories import (
    MovieRepository,
    ScreeningRepository,
    ScreeningSummary,
)
from marquise.domain.value_objects import MovieId


class GetMovieScreeningsUseCase:
    """Use case for listing all of a movie's screenings.

    No filtering beyond the movie scope is supported here — use
    ``SearchScreeningsQuery`` (``GET /v1/screenings``) for date range,
    cinema, or language filters.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching a movie's screenings.

        Attributes:
            movie_id: The movie to fetch screenings for.
            page: Page number (1-based). Ignored when size is None.
            size: Max number of screenings per page. If None, all matching
                screenings are returned unbounded (page is ignored).
        """

        movie_id: str
        page: int = 1
        size: int | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If movie_id is empty, size is provided but not
                    positive, or page is less than 1.
            """
            if not self.movie_id.strip():
                raise ValueError("movie_id must not be empty")
            if self.size is not None and self.size < 1:
                raise ValueError("size must be positive when provided")
            if self.page < 1:
                raise ValueError("page must be at least 1")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the movie's screenings.

        Attributes:
            movie_id: The movie's ID.
            movie_title: The movie's title.
            screenings: The matching page of screenings, ordered by showtime.
            total: Total number of screenings for the movie, ignoring
                limit/offset.
        """

        movie_id: str
        movie_title: str
        screenings: tuple[ScreeningSummary, ...]
        total: int

    def __init__(
        self,
        movie_repository: MovieRepository,
        screening_repository: ScreeningRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            movie_repository: A repository for querying movies.
            screening_repository: A repository for querying screenings.
        """
        self.movie_repository = movie_repository
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """List all of a movie's screenings.

        Args:
            request: The input data with movie ID and pagination
                parameters.

        Returns:
            The output data with the movie, its page of screenings, and the
            total count.

        Raises:
            MovieNotFoundError: If no movie with the given ID exists.
        """
        movie_id = MovieId(value=request.movie_id)
        if not await self.movie_repository.exists_by_id(movie_id):
            raise MovieNotFoundError(
                f"A movie with ID '{request.movie_id}' was not found"
            )
        movie = await self.movie_repository.find_by_id(movie_id)
        assert movie is not None  # existence already verified above

        if request.size is not None:
            limit = request.size
            offset = (request.page - 1) * request.size
        else:
            limit = None
            offset = 0

        page = await self.screening_repository.search(
            movie_id=movie_id,
            limit=limit,
            offset=offset,
        )

        return self.OutputData(
            movie_id=str(movie.id),
            movie_title=movie.title,
            screenings=tuple(page.items),
            total=page.total,
        )
