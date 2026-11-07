"""Command use case: create the movies that are missing from storage."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from uuid import uuid4

from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId

logger = logging.getLogger(__name__)


class CreateMoviesCommand:
    """Create one movie per key and tie every source movie to it.

    Source movies sharing a key are one film, so they share one movie.
    Existing details are never updated.
    """

    @dataclass(frozen=True, slots=True)
    class MovieInput:
        title: str
        saved_title: str
        key: str
        source_identifier: str | None = None
        tmdb_id: str | None = None
        release_year: int | None = None
        description: str | None = None
        directors: tuple[str, ...] | None = None
        cast: tuple[str, ...] | None = None
        duration_minutes: int | None = None
        poster_url: str | None = None
        trailer_url: str | None = None
        genres: tuple[str, ...] | None = None
        original_title: str | None = None
        rating: str | None = None
        origin_countries: tuple[str, ...] | None = None

        def __post_init__(self) -> None:
            for field in ("title", "saved_title", "key"):
                if not isinstance(getattr(self, field), str):
                    raise TypeError(f"{field} must be a string")
            self._check_optional(
                str,
                "source_identifier",
                "tmdb_id",
                "description",
                "poster_url",
                "trailer_url",
                "original_title",
                "rating",
            )
            self._check_optional(int, "release_year", "duration_minutes")
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
        movies: tuple[CreateMoviesCommand.MovieInput, ...]

        def __post_init__(self) -> None:
            if not isinstance(self.movies, tuple):
                raise TypeError("movies must be a tuple")
            for movie in self.movies:
                if not isinstance(movie, CreateMoviesCommand.MovieInput):
                    raise TypeError("movies must only contain MovieInput")

    @dataclass(frozen=True, slots=True)
    class CreatedMovie:
        title: str
        source_identifier: str | None
        movie_id: str
        tmdb_id: str | None

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movies: tuple[CreateMoviesCommand.CreatedMovie, ...]

    def __init__(self, movie_repository: MovieRepository) -> None:
        self._movie_repository = movie_repository

    async def execute(self, input_data: InputData) -> OutputData:
        """Create one movie per key.

        Args:
            input_data: The missing movies, keyed by the film they belong to.

        Returns:
            Every source movie tied to the movie created for its key.
        """
        distinct_movies = self._pick_one_per_key(input_data.movies)
        saved_movies = await self._save_all(distinct_movies)
        logger.info("Created %d movies", len(saved_movies))
        return self.OutputData(
            movies=self._tie_to_saved(input_data.movies, saved_movies)
        )

    @staticmethod
    def _pick_one_per_key(movies: tuple[MovieInput, ...]) -> dict[str, MovieInput]:
        """Pick one movie to create per key.

        A movie with a TMDB identity replaces one without, because it carries
        the identity. Among movies without one, the first one wins.
        """
        unmatched = {
            movie.key: movie for movie in reversed(movies) if movie.tmdb_id is None
        }
        matched = {movie.key: movie for movie in movies if movie.tmdb_id is not None}
        return unmatched | matched

    async def _save_all(self, movies: dict[str, MovieInput]) -> dict[str, Movie]:
        """Create or reuse each distinct film without updating existing details."""
        saved_movies = await asyncio.gather(
            *(
                self._movie_repository.create_or_reuse(self._build_movie(movie))
                for movie in movies.values()
            )
        )
        return dict(zip(movies, saved_movies, strict=True))

    @staticmethod
    def _build_movie(movie: MovieInput) -> Movie:
        """Build a new movie entity from one missing source movie."""
        return Movie(
            id=MovieId(value=uuid4().hex),
            title=movie.saved_title,
            description=movie.description,
            directors=movie.directors,
            cast=movie.cast,
            duration_minutes=movie.duration_minutes,
            release_year=movie.release_year,
            poster_url=movie.poster_url,
            trailer_url=movie.trailer_url,
            genres=movie.genres,
            original_title=movie.original_title,
            rating=movie.rating,
            origin_countries=movie.origin_countries,
            tmdb_id=movie.tmdb_id,
        )

    def _tie_to_saved(
        self, movies: tuple[MovieInput, ...], saved_movies: dict[str, Movie]
    ) -> tuple[CreatedMovie, ...]:
        """Tie every source movie to the movie saved for its key."""
        return tuple(
            self.CreatedMovie(
                movie.title,
                movie.source_identifier,
                saved_movies[movie.key].id.value,
                movie.tmdb_id,
            )
            for movie in movies
        )
