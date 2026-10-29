"""Command use case: create movies that don't yet exist in the database."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from uuid import uuid4

from marquise.application.exceptions.movie import MovieIdentityConflictError
from marquise.application.repositories import MovieRepository
from marquise.application.repositories.tmdb_search import TmdbSearch
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId

logger = logging.getLogger(__name__)


class CreateMissingMoviesCommand:
    """Create movies for titles not yet in the database.

    Takes movie metadata (already fetched by the caller), looks up each
    title, and persists only the missing ones.  Never updates existing
    movies.  Returns a flat list of MovieData so callers can link
    screenings to their movie.
    """

    @dataclass(frozen=True, slots=True)
    class MovieInput:
        title: str
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
        tmdb_id: str | None = None

        def __post_init__(self) -> None:
            if not self.title.strip():
                raise ValueError("title must not be empty")

    @dataclass(frozen=True, slots=True)
    class MovieData:
        title: str
        id: str

        def __post_init__(self) -> None:
            if not self.title.strip():
                raise ValueError("title must not be empty")
            if not self.id.strip():
                raise ValueError("id must not be empty")

    @dataclass(frozen=True, slots=True)
    class InputData:
        movies: tuple[CreateMissingMoviesCommand.MovieInput, ...]

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movies: tuple[CreateMissingMoviesCommand.MovieData, ...]

    def __init__(
        self, movie_repository: MovieRepository, tmdb_search: TmdbSearch | None = None
    ) -> None:
        self.movie_repository = movie_repository
        self.tmdb_search = tmdb_search

    async def execute(self, request: InputData) -> OutputData:
        resolved, unmatched = await self._resolve_tmdb(request.movies)
        found_movies = await self.movie_repository.find_by_titles(
            self._search_terms(unmatched)
        )
        existing, missing = self._separate_existing(unmatched, found_movies)
        created = await self._save_missing(missing)
        movies = resolved + existing + self._created_data(unmatched, created)

        logger.info(
            "Created %d new movies, found %d existing",
            len(created),
            len(found_movies),
        )
        return self.OutputData(movies=tuple(movies))

    async def _resolve_tmdb(
        self, movies: tuple[MovieInput, ...]
    ) -> tuple[list[MovieData], tuple[MovieInput, ...]]:
        """Reuse known TMDB movies before trying the old title lookup."""
        if self.tmdb_search is None:
            return [], movies
        resolved: list[CreateMissingMoviesCommand.MovieData] = []
        remaining: list[CreateMissingMoviesCommand.MovieInput] = []
        for movie in movies:
            candidates = await self.tmdb_search.search(movie.title, movie.release_year)
            if len(candidates) != 1:
                remaining.append(movie)
                continue
            tmdb_id = candidates[0].id
            existing = await self.movie_repository.find_by_tmdb_id(tmdb_id)
            if existing is not None:
                resolved.append(
                    self.MovieData(
                        self._normalize_title(movie.title), existing.id.value
                    )
                )
            else:
                remaining.append(replace(movie, tmdb_id=tmdb_id))
        return resolved, tuple(remaining)

    @staticmethod
    def _search_terms(movies: tuple[MovieInput, ...]) -> list[str]:
        """Choose one broad database search term per canonical title."""
        return [
            max(key.split(), key=len)
            for movie in movies
            if (key := Movie.title_key(movie.title))
        ]

    @classmethod
    def _separate_existing(
        cls,
        movie_inputs: tuple[MovieInput, ...],
        found_movies: list[Movie],
    ) -> tuple[list[MovieData], dict[str, MovieInput]]:
        """Return existing movie data and one pending input per title key."""
        candidates = cls._candidates_by_key(found_movies)
        existing: list[CreateMissingMoviesCommand.MovieData] = []
        missing: dict[str, CreateMissingMoviesCommand.MovieInput] = {}

        for movie_input in movie_inputs:
            title = cls._normalize_title(movie_input.title)
            key = Movie.title_key(title)
            movie = cls._find_match(
                candidates.get(key, []),
                title=title,
                release_year=movie_input.release_year,
            )
            if movie is not None:
                if (
                    movie_input.tmdb_id is not None
                    and movie.tmdb_id is not None
                    and movie_input.tmdb_id != movie.tmdb_id
                ):
                    raise MovieIdentityConflictError(
                        f"Movie '{title}' already has a different TMDB id"
                    )
                existing.append(cls.MovieData(title=title, id=movie.id.value))
            else:
                missing.setdefault(key, movie_input)
        return existing, missing

    async def _save_missing(self, missing: dict[str, MovieInput]) -> dict[str, Movie]:
        """Save each distinct TMDB film once, mapping all source titles back."""
        first_by_tmdb: dict[str, str] = {}
        unique: dict[str, CreateMissingMoviesCommand.MovieInput] = {}
        duplicates: dict[str, str] = {}
        for key, movie in missing.items():
            if movie.tmdb_id is not None and movie.tmdb_id in first_by_tmdb:
                duplicates[key] = first_by_tmdb[movie.tmdb_id]
            else:
                unique[key] = movie
                if movie.tmdb_id is not None:
                    first_by_tmdb[movie.tmdb_id] = key
        saved = await asyncio.gather(
            *(
                self.movie_repository.save(self._movie(movie))
                for movie in unique.values()
            )
        )
        created = dict(zip(unique, saved, strict=True))
        created.update({key: created[first] for key, first in duplicates.items()})
        return created

    @classmethod
    def _created_data(
        cls,
        movie_inputs: tuple[MovieInput, ...],
        created: dict[str, Movie],
    ) -> list[MovieData]:
        """Build output rows for every input represented by a created movie."""
        return [
            cls.MovieData(
                title=cls._normalize_title(movie_input.title),
                id=movie.id.value,
            )
            for movie_input in movie_inputs
            if (movie := created.get(Movie.title_key(movie_input.title))) is not None
        ]

    @staticmethod
    def _candidates_by_key(found_movies: list[Movie]) -> dict[str, list[Movie]]:
        """Group database search candidates by canonical title key."""
        candidates: dict[str, list[Movie]] = {}
        for movie in found_movies:
            candidates.setdefault(Movie.title_key(movie.title), []).append(movie)
        return candidates

    @staticmethod
    def _movie(movie_input: MovieInput) -> Movie:
        """Build a new movie entity from one scraped input."""
        return Movie(
            id=MovieId(value=uuid4().hex),
            title=CreateMissingMoviesCommand._normalize_title(movie_input.title),
            description=movie_input.description,
            directors=movie_input.directors,
            cast=movie_input.cast,
            duration_minutes=movie_input.duration_minutes,
            release_year=movie_input.release_year,
            poster_url=movie_input.poster_url,
            trailer_url=movie_input.trailer_url,
            genres=movie_input.genres,
            original_title=movie_input.original_title,
            rating=movie_input.rating,
            origin_countries=movie_input.origin_countries,
            tmdb_id=movie_input.tmdb_id,
        )

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Strip and collapse internal whitespace in a scraped movie title."""
        return " ".join(title.strip().split())

    @classmethod
    def _find_match(
        cls,
        candidates: list[Movie],
        *,
        title: str,
        release_year: int | None,
    ) -> Movie | None:
        """Return one compatible movie candidate, or None when ambiguous."""
        compatible = [
            movie
            for movie in candidates
            if release_year is None
            or movie.release_year is None
            or movie.release_year == release_year
        ]
        exact = [
            movie
            for movie in compatible
            if cls._normalize_title(movie.title).casefold()
            == cls._normalize_title(title).casefold()
        ]
        if len(exact) == 1:
            return exact[0]
        return compatible[0] if len(compatible) == 1 else None
