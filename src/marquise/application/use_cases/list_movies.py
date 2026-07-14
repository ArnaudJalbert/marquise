"""List movies use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.repositories import MovieRepository


class ListMoviesUseCase:
    """Use case for listing movies with optional title filtering."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing movies.

        Attributes:
            title: Optional title filter (substring, case-insensitive).
            page: Page number (1-based). Ignored when size is None.
            size: Max number of items per page. If None, all matching
                movies are returned unbounded (page is ignored).
        """

        title: str | None = None
        page: int = 1
        size: int | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If title is provided but empty or whitespace-only,
                    if size is provided but not positive, or if page is less
                    than 1.
            """
            if self.title is not None and not self.title.strip():
                raise ValueError("title must not be empty when provided")
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

    async def execute(self, request: InputData) -> OutputData:
        """List movies, optionally filtered by title and paginated.

        Args:
            request: The input data containing optional title filter and
                pagination parameters.

        Returns:
            The output data containing the matching page of movies and the
            total count.
        """
        if request.size is not None:
            limit = request.size
            offset = (request.page - 1) * request.size
        else:
            limit = None
            offset = 0

        page = await self.movie_repository.find_all(
            title_filter=request.title,
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

        return self.OutputData(movies=movie_data, total=page.total)
