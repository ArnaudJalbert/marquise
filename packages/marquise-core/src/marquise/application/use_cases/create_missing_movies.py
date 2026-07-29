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
    movies.  Returns a title-to-ID lookup so callers can link screenings
    to their movie.
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
    class InputData:
        movies: tuple[CreateMissingMoviesCommand.MovieInput, ...]

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movie_lookup: dict[str, str]

    def __init__(self, movie_repository: MovieRepository) -> None:
        self.movie_repository = movie_repository

    async def execute(self, request: InputData) -> OutputData:
        titles = [_normalize_title(m.title) for m in request.movies]
        found_map = await self.movie_repository.find_by_titles(titles)

        movie_lookup: dict[str, str] = {}
        to_create: list[Movie] = []

        existing_count = sum(1 for v in found_map.values() if v is not None)
        logger.info(
            "Processing %d movie inputs, %d already exist",
            len(request.movies),
            existing_count,
        )

        created_titles: set[str] = set()
        for movie_input in request.movies:
            title = _normalize_title(movie_input.title)
            existing = found_map.get(title)
            if existing is not None:
                movie_lookup[title] = existing.id.value
            elif title not in created_titles:
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
                created_titles.add(title)

        if to_create:
            saved = await asyncio.gather(
                *[self.movie_repository.save(m) for m in to_create]
            )
            for movie, saved_movie in zip(to_create, saved):
                movie_lookup[_normalize_title(movie.title)] = saved_movie.id.value

        logger.info(
            "Created %d new movies, found %d existing",
            len(to_create),
            existing_count,
        )

        return self.OutputData(movie_lookup=movie_lookup)


def _normalize_title(title: str) -> str:
    """Strip and collapse internal whitespace in a scraped movie title."""
    return " ".join(title.strip().split())
