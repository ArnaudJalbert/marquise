"""Controller for movie read operations."""

from __future__ import annotations

from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.get_movie_screenings import (
    GetMovieScreeningsUseCase,
)
from marquise.application.use_cases.get_movies_by_ids import GetMoviesByIdsUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase


class MovieController:
    """Handles movie read flows.

    All methods are public — no authentication required.  Use case instances
    are injected at construction time.
    """

    def __init__(
        self,
        get_movie_use_case: GetMovieUseCase,
        get_movie_screenings_use_case: GetMovieScreeningsUseCase,
        get_movies_by_ids_use_case: GetMoviesByIdsUseCase,
        list_movies_use_case: ListMoviesUseCase,
    ) -> None:
        self._get_use_case = get_movie_use_case
        self._get_screenings_use_case = get_movie_screenings_use_case
        self._get_by_ids_use_case = get_movies_by_ids_use_case
        self._list_use_case = list_movies_use_case

    async def list(
        self,
        title: str | None = None,
        page: int = 1,
        size: int | None = None,
    ) -> ListMoviesUseCase.OutputData:
        """List movies, optionally filtered by title and paginated.

        This is a public operation — no authentication required.

        Args:
            title: Optional title filter (case-insensitive substring).
            page: Page number (1-based). Ignored when size is None.
            size: Max number of items per page. If None, all matching
                movies are returned unbounded (page is ignored).

        Returns:
            The output data containing the matching page of movies and the
            total count.
        """
        request = ListMoviesUseCase.InputData(title=title, page=page, size=size)
        return await self._list_use_case.execute(request)

    async def get(self, movie_id: str) -> GetMovieUseCase.OutputData:
        """Retrieve a single movie by its ID.

        This is a public operation — no authentication required.

        Args:
            movie_id: The ID of the movie to retrieve.

        Returns:
            The output data describing the movie.

        Raises:
            MovieNotFoundError: If no movie with the given ID exists.
        """
        request = GetMovieUseCase.InputData(movie_id=movie_id)
        return await self._get_use_case.execute(request)

    async def get_by_ids(
        self, movie_ids: list[str]
    ) -> GetMoviesByIdsUseCase.OutputData:
        """Retrieve multiple movies by their IDs in one call.

        This is a public operation — no authentication required.

        Args:
            movie_ids: The IDs of the movies to retrieve.

        Returns:
            The output data describing the matching movies. IDs with no
            matching movie are silently omitted.

        Raises:
            TooManyMovieIdsError: If more IDs are requested than allowed.
        """
        request = GetMoviesByIdsUseCase.InputData(movie_ids=tuple(movie_ids))
        return await self._get_by_ids_use_case.execute(request)

    async def get_screenings(
        self,
        movie_id: str,
        page: int = 1,
        size: int | None = None,
    ) -> GetMovieScreeningsUseCase.OutputData:
        """List all of a movie's screenings.

        This is a public operation — no authentication required.

        Args:
            movie_id: The movie to fetch screenings for.
            page: Page number (1-based). Ignored when size is None.
            size: Max number of screenings per page. If None, all matching
                screenings are returned unbounded (page is ignored).

        Returns:
            The output data with the movie, its page of screenings, and the
            total count.

        Raises:
            MovieNotFoundError: If no movie with the given ID exists.
        """
        request = GetMovieScreeningsUseCase.InputData(
            movie_id=movie_id, page=page, size=size
        )
        return await self._get_screenings_use_case.execute(request)
