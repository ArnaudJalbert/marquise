"""Get movie by ID use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.repositories import MovieRepository
from marquise.domain.value_objects import MovieId


class GetMovieUseCase:
    """Use case for retrieving a single movie by its ID."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching a movie.

        Attributes:
            movie_id: The unique identifier of the movie.
        """

        movie_id: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If movie_id is empty or whitespace-only.
            """
            if not self.movie_id.strip():
                raise ValueError("movie_id must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """The retrieved movie's output data.

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
            tmdb_rating: TMDB user score out of ten (optional).
            tmdb_vote_count: Number of TMDB user votes (optional).
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
        tmdb_rating: float | None = None
        tmdb_vote_count: int | None = None

    def __init__(self, movie_repository: MovieRepository) -> None:
        """Initialize the use case.

        Args:
            movie_repository: A repository for querying movies.
        """
        self.movie_repository = movie_repository

    async def execute(self, request: InputData) -> OutputData:
        """Retrieve a movie by its ID.

        Args:
            request: The input data containing the movie ID.

        Returns:
            The output data describing the movie.

        Raises:
            MovieNotFoundError: If no movie with the given ID exists.
        """
        movie = await self.movie_repository.find_by_id(MovieId(value=request.movie_id))
        if movie is None:
            raise MovieNotFoundError(
                f"A movie with ID '{request.movie_id}' was not found"
            )

        return self.OutputData(
            id=str(movie.id),
            title=movie.title,
            release_year=movie.release_year,
            directors=movie.directors,
            cast=movie.cast,
            duration_minutes=movie.duration_minutes,
            description=movie.description,
            poster_url=movie.poster_url,
            trailer_url=movie.trailer_url,
            genres=movie.genres,
            original_title=movie.original_title,
            rating=movie.rating,
            origin_countries=movie.origin_countries,
            tmdb_rating=movie.tmdb_rating,
            tmdb_vote_count=movie.tmdb_vote_count,
        )
