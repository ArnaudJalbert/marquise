"""Get all of a movie's screenings use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.repositories import MovieRepository, ScreeningRepository
from marquise.domain.value_objects import MovieId


class GetMovieScreeningsUseCase:
    """Use case for listing all of a movie's screenings.

    No filtering beyond the movie scope is supported here — use
    ``SearchScreeningsUseCase`` (``GET /v1/screenings``) for date range,
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
        screenings: tuple[GetMovieScreeningsUseCase.ScreeningData, ...]
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
        movie = await self.movie_repository.find_by_id(movie_id)
        if movie is None:
            raise MovieNotFoundError(
                f"A movie with ID '{request.movie_id}' was not found"
            )

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

        return self.OutputData(
            movie_id=str(movie.id),
            movie_title=movie.title,
            screenings=screening_data,
            total=page.total,
        )
