"""List movies use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import TooManyMovieIdsError
from marquise.application.page import calculate_page_offset
from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId

MAX_MOVIE_IDS = 100


class ListMoviesUseCase:
    """Use case for listing movies, optionally filtered by title or by IDs."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing movies.

        Attributes:
            title: Optional title filter (substring, case-insensitive). May
                be combined with ids, in which case both filters apply (AND).
            ids: Optional list of movie IDs to fetch in bulk. May be
                combined with title. At most MAX_MOVIE_IDS ids, and the
                count must not exceed size.
            page: Page number (1-based). Must be 1 when ids is provided.
            size: Max number of items per page.
        """

        page: int
        size: int
        title: str | None = None
        ids: tuple[str, ...] | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If title is provided but empty or whitespace-only,
                    if size is not positive, if page is less than 1, if ids
                    is provided but empty, if ids' count exceeds size, or if
                    page is not 1 when ids is provided.
                TooManyMovieIdsError: If more than MAX_MOVIE_IDS ids are
                    requested.
            """
            if self.title is not None and not self.title.strip():
                raise ValueError("title must not be empty when provided")
            if self.size < 1:
                raise ValueError("size must be positive")
            if self.page < 1:
                raise ValueError("page must be at least 1")
            if self.ids is not None:
                if len(self.ids) == 0:
                    raise ValueError("ids must not be empty when provided")
                if len(self.ids) > MAX_MOVIE_IDS:
                    raise TooManyMovieIdsError(
                        f"At most {MAX_MOVIE_IDS} ids may be requested at"
                        f" once, got {len(self.ids)}"
                    )
                if len(self.ids) > self.size:
                    raise ValueError("ids count must not exceed size")
                if self.page != 1:
                    raise ValueError("page must be 1 when ids is provided")

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

        def __post_init__(self) -> None:
            """Validate movie data.

            Raises:
                ValueError: If id or title is empty.
            """
            if not self.id.strip():
                raise ValueError("id must not be empty")
            if not self.title.strip():
                raise ValueError("title must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the list of movies.

        Attributes:
            movies: The page of matching movies.
            total: Total number of movies matching the filter, ignoring
                limit/offset.
        """

        movies: list[ListMoviesUseCase.MovieData]
        total: int

        def __post_init__(self) -> None:
            """Validate output data.

            Raises:
                ValueError: If total is negative.
            """
            if self.total < 0:
                raise ValueError("total must not be negative")

    def __init__(self, movie_repository: MovieRepository) -> None:
        """Initialize the use case.

        Args:
            movie_repository: A repository for querying movies.
        """
        self.movie_repository = movie_repository

    async def execute(self, input_data: InputData) -> OutputData:
        """List movies, optionally filtered by title/ids and paginated.

        Args:
            input_data: The input data containing optional title or ids filter
                and pagination parameters.

        Returns:
            The output data containing the matching page of movies and the
            total count.
        """
        if input_data.ids is not None:
            movies = await self.movie_repository.find_by_ids(
                [MovieId(value=movie_id) for movie_id in input_data.ids]
            )
            if input_data.title is not None:
                needle = input_data.title.lower()
                movies = [m for m in movies if needle in m.title.lower()]
            movie_data = [self._to_movie_data(m) for m in movies]
            return self.OutputData(movies=movie_data, total=len(movie_data))

        page = await self.movie_repository.find_all(
            title_filter=input_data.title,
            limit=input_data.size,
            offset=calculate_page_offset(input_data.page, input_data.size),
        )

        movie_data = [self._to_movie_data(m) for m in page.items]

        return self.OutputData(movies=movie_data, total=page.total)

    @staticmethod
    def _to_movie_data(movie: Movie) -> ListMoviesUseCase.MovieData:
        """Map a Movie domain entity to this use case's MovieData output.

        Args:
            movie: The domain entity to map.

        Returns:
            The mapped MovieData.
        """
        return ListMoviesUseCase.MovieData(
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
