"""Supabase repository implementation of MovieRepository.

Adapts a ``MovieGateway`` (infrastructure) into the ``MovieRepository``
interface (application).  No SQL, no asyncpg — pure entity mapping.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from marquise.interface_adapters.repositories.protocols.movie import MovieGateway


class SupabaseMovieRepository(MovieRepository):
    """Movie repository backed by a Supabase PostgreSQL database.

    Parameters
    ----------
    gateway:
        A data gateway that implements ``MovieGateway``.
    """

    def __init__(self, gateway: MovieGateway) -> None:
        self._gateway = gateway

    async def save(self, movie: Movie) -> Movie:
        """Persist a movie via the gateway and return the mapped entity.

        Args:
            movie: The movie domain entity to save.

        Returns:
            The saved movie with server-assigned fields.
        """
        data = await self._gateway.save(
            movie_id=str(movie.id),
            title=movie.title,
            release_date=movie.release_date,
            directors=",".join(movie.directors)
            if movie.directors is not None
            else None,
            cast=",".join(movie.cast) if movie.cast is not None else None,
            duration_minutes=movie.duration_minutes,
            description=movie.description,
        )
        return self._to_entity(data)

    async def find_by_id(self, movie_id: MovieId) -> Optional[Movie]:
        """Retrieve a movie by ID.

        Args:
            movie_id: The unique identifier of the movie.

        Returns:
            The matching movie entity, or None if not found.
        """
        data = await self._gateway.find_by_id(movie_id=str(movie_id))
        return self._to_entity(data) if data is not None else None

    async def find_by_title(self, title: str) -> Optional[Movie]:
        """Find a movie by its exact title.

        Args:
            title: The movie title to search for.

        Returns:
            The matching movie entity, or None if not found.
        """
        data = await self._gateway.find_by_title(title=title)
        return self._to_entity(data) if data is not None else None

    @staticmethod
    def _to_entity(data: dict) -> Movie:
        """Map a raw gateway dict to a Movie domain entity.

        Args:
            data: The dict returned by the gateway.

        Returns:
            A new Movie entity populated with the dict values.
        """
        raw_directors = data.get("directors")
        if raw_directors:
            directors = tuple(raw_directors.split(","))
        else:
            directors = None
        raw_cast = data.get("cast_members")
        cast = tuple(raw_cast.split(",")) if raw_cast else None
        release_date = data["release_date"]
        if isinstance(release_date, str):
            release_date = date.fromisoformat(release_date)
        return Movie(
            id=MovieId(value=data["id"]),
            title=data["title"],
            release_date=release_date,
            directors=directors,
            cast=cast,
            duration_minutes=data.get("duration_minutes"),
            description=data.get("description"),
        )
