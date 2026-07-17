"""Get movies by a list of IDs use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import TooManyMovieIdsError
from marquise.application.repositories import MovieRepository
from marquise.domain.value_objects import MovieId

MAX_MOVIE_IDS = 100


class GetMoviesByIdsUseCase:
    """Use case for retrieving multiple movies by their IDs in one call."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching movies in bulk.

        Attributes:
            movie_ids: The unique identifiers of the movies to fetch.
        """

        movie_ids: tuple[str, ...]

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If movie_ids is empty.
                TooManyMovieIdsError: If more than ``MAX_MOVIE_IDS`` IDs are
                    requested.
            """
            if not self.movie_ids:
                raise ValueError("movie_ids must not be empty")
            if len(self.movie_ids) > MAX_MOVIE_IDS:
                raise TooManyMovieIdsError(
                    f"At most {MAX_MOVIE_IDS} movie_ids may be requested at"
                    f" once, got {len(self.movie_ids)}"
                )

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
        """Output data containing the fetched movies.

        Attributes:
            movies: The matching movies. IDs with no matching movie are
                silently omitted — this may be shorter than the requested
                ``movie_ids``.
        """

        movies: tuple[GetMoviesByIdsUseCase.MovieData, ...]

    def __init__(self, movie_repository: MovieRepository) -> None:
        """Initialize the use case.

        Args:
            movie_repository: A repository for querying movies.
        """
        self.movie_repository = movie_repository

    async def execute(self, request: InputData) -> OutputData:
        """Retrieve movies by their IDs.

        Args:
            request: The input data containing the movie IDs.

        Returns:
            The output data describing the matching movies.
        """
        movies = await self.movie_repository.find_by_ids(
            [MovieId(value=movie_id) for movie_id in request.movie_ids]
        )

        movie_data = tuple(
            self.MovieData(
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
            )
            for movie in movies
        )

        return self.OutputData(movies=movie_data)
