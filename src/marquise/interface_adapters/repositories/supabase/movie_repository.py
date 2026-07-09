"""Supabase repository implementation of MovieRepository.

Adapts a ``MovieGateway`` (infrastructure) into the ``MovieRepository``
interface (application).  No SQL, no asyncpg — pure entity mapping.
"""

from __future__ import annotations

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
            release_year=movie.release_year,
            directors=",".join(movie.directors)
            if movie.directors is not None
            else None,
            cast=",".join(movie.cast) if movie.cast is not None else None,
            duration_minutes=movie.duration_minutes,
            description=movie.description,
            poster_url=movie.poster_url,
            trailer_url=movie.trailer_url,
            genres=",".join(movie.genres) if movie.genres is not None else None,
            original_title=movie.original_title,
            rating=movie.rating,
            origin_countries=",".join(movie.origin_countries)
            if movie.origin_countries is not None
            else None,
        )
        return self._to_entity(data)

    async def find_by_id(self, movie_id: MovieId) -> Movie | None:
        """Retrieve a movie by ID.

        Args:
            movie_id: The unique identifier of the movie.

        Returns:
            The matching movie entity, or None if not found.
        """
        data = await self._gateway.find_by_id(movie_id=str(movie_id))
        return self._to_entity(data) if data is not None else None

    async def find_by_title(self, title: str) -> Movie | None:
        """Find a movie by title, case-insensitively.

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
        raw_genres = data.get("genres")
        genres = tuple(raw_genres.split(",")) if raw_genres else None
        raw_origin_countries = data.get("origin_countries")
        origin_countries = (
            tuple(raw_origin_countries.split(",")) if raw_origin_countries else None
        )
        return Movie(
            id=MovieId(value=data["id"]),
            title=data["title"],
            release_year=data.get("release_year"),
            directors=directors,
            cast=cast,
            duration_minutes=data.get("duration_minutes"),
            description=data.get("description"),
            poster_url=data.get("poster_url"),
            trailer_url=data.get("trailer_url"),
            genres=genres,
            original_title=data.get("original_title"),
            rating=data.get("rating"),
            origin_countries=origin_countries,
        )
