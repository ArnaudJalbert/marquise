"""Command use case: create movies that don't yet exist in the database."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from uuid import uuid4

from marquise.application.repositories import MovieRepository
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

    def __init__(self, movie_repository: MovieRepository) -> None:
        self.movie_repository = movie_repository

    async def execute(self, request: InputData) -> OutputData:
        titles = [_normalize_title(m.title) for m in request.movies]
        found_movies = await self.movie_repository.find_by_titles(titles)

        found_map: dict[str, Movie] = {}
        for movie in found_movies:
            found_map[_title_key(movie.title)] = movie

        movies_data: list[CreateMissingMoviesCommand.MovieData] = []
        to_create: list[Movie] = []

        logger.info(
            "Processing %d movie inputs, %d already exist",
            len(request.movies),
            len(found_movies),
        )

        created_titles: set[str] = set()
        for movie_input in request.movies:
            title = _normalize_title(movie_input.title)
            existing = found_map.get(_title_key(title))
            if existing is not None:
                movies_data.append(self.MovieData(title=title, id=existing.id.value))
            elif _title_key(title) not in created_titles:
                movie = Movie(
                    id=MovieId(value=uuid4().hex),
                    title=title,
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
                )
                to_create.append(movie)
                created_titles.add(_title_key(title))

        if to_create:
            saved = await asyncio.gather(
                *[self.movie_repository.save(m) for m in to_create]
            )
            created_map = {_title_key(movie.title): movie for movie in saved}
            for movie_input in request.movies:
                if _title_key(movie_input.title) not in found_map:
                    movie = created_map.get(_title_key(movie_input.title))
                    if movie is not None:
                        movies_data.append(
                            self.MovieData(
                                title=_normalize_title(movie_input.title),
                                id=movie.id.value,
                            )
                        )

        logger.info(
            "Created %d new movies, found %d existing",
            len(to_create),
            len(found_movies),
        )

        return self.OutputData(movies=tuple(movies_data))


def _normalize_title(title: str) -> str:
    """Strip and collapse internal whitespace in a scraped movie title."""
    return " ".join(title.strip().split())


def _title_key(title: str) -> str:
    """Build a forgiving key for titles from different cinema sources."""
    words = "".join(
        char if char.isalnum() else " " for char in title.casefold()
    ).split()
    if len(words) > 1 and words[0] in {"a", "an", "the"}:
        words.pop(0)
    return " ".join(words)
