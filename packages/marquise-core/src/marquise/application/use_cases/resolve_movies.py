"""Command use case: tie each source movie to its stored movie."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
    from marquise.application.use_cases.create_movies import CreateMoviesCommand
    from marquise.application.use_cases.match_movies import MatchMoviesUseCase

logger = logging.getLogger(__name__)


class ResolveMoviesCommand:
    """Coordinate matching, the stored movie lookup and movie creation.

    Only sequences use cases and reformats data between them.
    """

    @dataclass(frozen=True, slots=True)
    class MovieInput:
        title: str
        source_identifier: str | None = None
        identity_title: str | None = None
        description: str | None = None
        directors: tuple[str, ...] | None = None
        cast: tuple[str, ...] | None = None
        duration_minutes: int | None = None
        release_year: int | None = None
        poster_url: str | None = None
        trailer_url: str | None = None
        genres: tuple[str, ...] | None = None
        original_title: str | None = None
        rating: str | None = None
        origin_countries: tuple[str, ...] | None = None

        def __post_init__(self) -> None:
            if not isinstance(self.title, str):
                raise TypeError("title must be a string")
            self._check_optional(
                str,
                "source_identifier",
                "identity_title",
                "description",
                "poster_url",
                "trailer_url",
                "original_title",
                "rating",
            )
            self._check_optional(int, "duration_minutes", "release_year")
            self._check_optional(
                tuple, "directors", "cast", "genres", "origin_countries"
            )

        def _check_optional(self, expected_type: type, *fields: str) -> None:
            for field in fields:
                value = getattr(self, field)
                if value is not None and not isinstance(value, expected_type):
                    raise TypeError(f"{field} must be a {expected_type.__name__}")

    @dataclass(frozen=True, slots=True)
    class InputData:
        movies: tuple[ResolveMoviesCommand.MovieInput, ...]

        def __post_init__(self) -> None:
            if not isinstance(self.movies, tuple):
                raise TypeError("movies must be a tuple")
            for movie in self.movies:
                if not isinstance(movie, ResolveMoviesCommand.MovieInput):
                    raise TypeError("movies must only contain MovieInput")

    @dataclass(frozen=True, slots=True)
    class ResolvedMovie:
        title: str
        source_identifier: str | None
        movie_id: str
        tmdb_id: str | None

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movies: tuple[ResolveMoviesCommand.ResolvedMovie, ...]

    def __init__(
        self,
        match_movies: MatchMoviesUseCase,
        find_stored_movies: FindStoredMoviesQuery,
        create_movies: CreateMoviesCommand,
    ) -> None:
        self._match_movies = match_movies
        self._find_stored_movies = find_stored_movies
        self._create_movies = create_movies

    async def execute(self, input_data: InputData) -> OutputData:
        """Tie each source movie to a stored movie, creating the missing ones.

        Args:
            input_data: The source movies.

        Returns:
            Every source movie with its movie ID, and its TMDB ID when known.
        """
        matches = await self._match_source_movies(input_data)
        movie_lookup = await self._look_up_stored_movies(matches)
        created_movies = await self._create_missing_movies(input_data, movie_lookup)
        logger.info("Resolved %d movies", len(input_data.movies))
        return self._build_output(movie_lookup, created_movies)

    async def _match_source_movies(
        self, input_data: InputData
    ) -> MatchMoviesUseCase.OutputData:
        """Find each source movie's identity."""
        request = self._build_match_request(input_data)
        return await self._match_movies.execute(request)

    def _build_match_request(
        self, input_data: InputData
    ) -> MatchMoviesUseCase.InputData:
        """Reformat source movies for matching."""
        return self._match_movies.InputData(
            movies=tuple(
                self._match_movies.MovieInput(
                    title=movie.title,
                    release_year=movie.release_year,
                    directors=movie.directors or (),
                    duration_minutes=movie.duration_minutes,
                    identity_title=movie.identity_title,
                    source_identifier=movie.source_identifier,
                )
                for movie in input_data.movies
            )
        )

    async def _look_up_stored_movies(
        self, matches: MatchMoviesUseCase.OutputData
    ) -> FindStoredMoviesQuery.OutputData:
        """Sort matched movies into stored and missing."""
        request = self._build_find_request(matches)
        return await self._find_stored_movies.execute(request)

    def _build_find_request(
        self, matches: MatchMoviesUseCase.OutputData
    ) -> FindStoredMoviesQuery.InputData:
        """Reformat matches for the stored movie lookup."""
        return self._find_stored_movies.InputData(
            movies=tuple(
                self._find_stored_movies.MovieInput(
                    title=match.source.title,
                    source_identifier=match.source.source_identifier,
                    release_year=match.source.release_year,
                    matched_release_year=match.release_year,
                    identity=match.identity,
                    matched_titles=match.titles,
                )
                for match in matches.matches
            )
        )

    async def _create_missing_movies(
        self, input_data: InputData, movie_lookup: FindStoredMoviesQuery.OutputData
    ) -> CreateMoviesCommand.OutputData:
        """Create the missing movies."""
        request = self._build_create_request(input_data, movie_lookup)
        return await self._create_movies.execute(request)

    def _build_create_request(
        self, input_data: InputData, movie_lookup: FindStoredMoviesQuery.OutputData
    ) -> CreateMoviesCommand.InputData:
        """Reformat missing movies, adding each one's source details."""
        details = {
            (movie.title, movie.source_identifier): movie for movie in input_data.movies
        }
        return self._create_movies.InputData(
            movies=tuple(
                self._build_create_input(
                    movie, details[(movie.title, movie.source_identifier)]
                )
                for movie in movie_lookup.missing
            )
        )

    def _build_create_input(
        self, missing: FindStoredMoviesQuery.MissingMovie, details: MovieInput
    ) -> CreateMoviesCommand.MovieInput:
        """Reformat one missing movie and its source details."""
        return self._create_movies.MovieInput(
            title=missing.title,
            saved_title=missing.saved_title,
            key=missing.key,
            source_identifier=missing.source_identifier,
            tmdb_id=missing.tmdb_id,
            release_year=missing.release_year,
            description=details.description,
            directors=details.directors,
            cast=details.cast,
            duration_minutes=details.duration_minutes,
            poster_url=details.poster_url,
            trailer_url=details.trailer_url,
            genres=details.genres,
            original_title=details.original_title,
            rating=details.rating,
            origin_countries=details.origin_countries,
        )

    def _build_output(
        self,
        movie_lookup: FindStoredMoviesQuery.OutputData,
        created_movies: CreateMoviesCommand.OutputData,
    ) -> OutputData:
        """Reformat stored and created movies as resolved movies."""
        return self.OutputData(
            movies=tuple(
                self.ResolvedMovie(
                    movie.title,
                    movie.source_identifier,
                    movie.movie_id,
                    movie.tmdb_id,
                )
                for movie in (*movie_lookup.stored, *created_movies.movies)
            )
        )
