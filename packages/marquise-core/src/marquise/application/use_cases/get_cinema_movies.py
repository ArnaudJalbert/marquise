"""Get a cinema's distinct movies within a date range use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import CinemaRepository, ScreeningRepository
from marquise.domain.value_objects import CinemaId


class GetCinemaMoviesUseCase:
    """Use case for listing the distinct movies screening at a cinema."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching a cinema's distinct movies.

        Attributes:
            cinema_id: The cinema to fetch movies for.
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).
            page: Page number (1-based). Ignored when size is None.
            size: Max number of movies per page. If None, all matching
                movies are returned unbounded (page is ignored).
        """

        cinema_id: str
        start_date: datetime
        end_date: datetime
        page: int = 1
        size: int | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If cinema_id is empty, the range is inverted,
                    size is provided but not positive, or page is less than 1.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            start = self.start_date.replace(tzinfo=self.start_date.tzinfo or UTC)
            end = self.end_date.replace(tzinfo=self.end_date.tzinfo or UTC)
            if start > end:
                raise ValueError("start_date must not be after end_date")
            if self.size is not None and self.size < 1:
                raise ValueError("size must be positive when provided")
            if self.page < 1:
                raise ValueError("page must be at least 1")

    @dataclass(frozen=True, slots=True)
    class MovieData:
        """A single movie's output data.

        Attributes:
            id: Unique identifier of the movie.
            title: Official title of the movie.
            release_year: Theatrical release year (optional).
            directors: Director names (optional).
            cast: Cast member names (optional).
            duration_minutes: Runtime in minutes (optional).
            description: Plot synopsis (optional).
            poster_url: URL to the poster image (optional).
            trailer_url: URL to the trailer (optional).
            genres: Genre names (optional).
            original_title: Original title (optional).
            rating: Content rating (optional).
            origin_countries: Production country names (optional).
        """

        id: str
        title: str
        release_year: int | None = None
        directors: tuple[str, ...] | None = None
        cast: tuple[str, ...] | None = None
        duration_minutes: int | None = None
        description: str | None = None
        poster_url: str | None = None
        trailer_url: str | None = None
        genres: tuple[str, ...] | None = None
        original_title: str | None = None
        rating: str | None = None
        origin_countries: tuple[str, ...] | None = None

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the cinema's distinct movies.

        Attributes:
            cinema_id: The cinema's ID.
            cinema_name: The cinema's display name.
            movies: The matching page of distinct movies.
            total: Total number of distinct movies matching the cinema and
                date range, ignoring limit/offset.
        """

        cinema_id: str
        cinema_name: str
        movies: list[GetCinemaMoviesUseCase.MovieData]
        total: int

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

    async def execute(self, input_data: InputData) -> OutputData:
        """List a cinema's distinct movies within the requested date range.

        Args:
            input_data: The input data with cinema ID, date range, and
                pagination parameters.

        Returns:
            The output data with the cinema, its page of distinct movies, and
            the total count.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        cinema_id = CinemaId(value=input_data.cinema_id)
        if not await self.cinema_repository.exists_by_id(cinema_id):
            raise CinemaNotFoundError(
                f"A cinema with ID '{input_data.cinema_id}' was not found"
            )
        cinema = await self.cinema_repository.find_by_id(cinema_id)
        assert cinema is not None  # existence already verified above

        if input_data.size is not None:
            limit = input_data.size
            offset = (input_data.page - 1) * input_data.size
        else:
            limit = None
            offset = 0

        page = await self.screening_repository.find_distinct_movies_by_cinema(
            cinema_id=cinema_id,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
            limit=limit,
            offset=offset,
        )

        movie_data = [
            self.MovieData(
                id=str(m.id),
                title=m.title,
                release_year=m.release_year,
                directors=m.directors,
                cast=m.cast,
                duration_minutes=m.duration_minutes,
                description=m.description,
                poster_url=m.poster_url,
                trailer_url=m.trailer_url,
                genres=m.genres,
                original_title=m.original_title,
                rating=m.rating,
                origin_countries=m.origin_countries,
            )
            for m in page.items
        ]

        return self.OutputData(
            cinema_id=str(cinema.id),
            cinema_name=cinema.name,
            movies=movie_data,
            total=page.total,
        )
