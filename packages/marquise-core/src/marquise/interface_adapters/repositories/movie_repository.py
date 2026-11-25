"""Postgres repository implementation of MovieRepository.

Adapts a ``MovieGateway`` (infrastructure) into the ``MovieRepository``
interface (application).  No SQL, no asyncpg — pure entity mapping.
"""

from __future__ import annotations

from marquise.application.page import Page
from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from marquise.interface_adapters.gateways.movie import MovieGateway
from marquise.interface_adapters.mappers import to_movie


class PostgresMovieRepository(MovieRepository):
    """Movie repository backed by a PostgreSQL database.

    Parameters
    ----------
    gateway:
        A data gateway that implements ``MovieGateway``.
    """

    def __init__(self, gateway: MovieGateway) -> None:
        self._gateway = gateway

    async def create_or_reuse(self, movie: Movie) -> Movie:
        """Create a movie, preserving details when a concurrent import won."""
        return await self._save(movie)

    async def _save(self, movie: Movie) -> Movie:
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
            tmdb_id=movie.tmdb_id,
            tmdb_rating=movie.tmdb_rating,
            tmdb_vote_count=movie.tmdb_vote_count,
            update_existing=False,
        )
        return to_movie(data)

    async def find_by_tmdb_id(self, tmdb_id: str) -> Movie | None:
        """Find a movie by its TMDB film id, or return None."""
        data = await self._gateway.find_by_tmdb_id(tmdb_id)
        return to_movie(data) if data is not None else None

    async def find_by_id(self, movie_id: MovieId) -> Movie | None:
        """Retrieve a movie by ID.

        Args:
            movie_id: The unique identifier of the movie.

        Returns:
            The matching movie entity, or None if not found.
        """
        data = await self._gateway.find_by_id(movie_id=str(movie_id))
        return to_movie(data) if data is not None else None

    async def find_by_ids(self, movie_ids: list[MovieId]) -> list[Movie]:
        """Retrieve movies by a list of unique identifiers.

        Args:
            movie_ids: The IDs of the movies to find.

        Returns:
            The matching movie entities. IDs with no matching movie are
            silently omitted.
        """
        data = await self._gateway.find_by_ids(
            movie_ids=[str(movie_id) for movie_id in movie_ids]
        )
        return [to_movie(row) for row in data]

    async def find_by_titles(self, titles: list[str]) -> list[Movie]:
        """Find candidate movies containing any title term, case-insensitively.

        Args:
            titles: The title terms to search for.

        Returns:
            A list of candidate Movie entities.
        """
        data = await self._gateway.find_by_titles(titles)
        return [to_movie(row) for row in data]

    async def exists_by_id(self, movie_id: MovieId) -> bool:
        """Check whether a movie exists with the given ID.

        Args:
            movie_id: The ID to check for.

        Returns:
            True if a movie with that ID exists, False otherwise.
        """
        return await self._gateway.exists_by_id(movie_id=str(movie_id))

    async def find_all(
        self,
        title_filter: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[Movie]:
        """Retrieve movies, optionally filtered by title and paginated.

        Args:
            title_filter: An optional substring to match against movie
                titles (case-insensitive). If None, all movies are returned.
            limit: Max number of movies to return. If None, all matching
                movies are returned unbounded.
            offset: Number of matching movies to skip before returning
                results.

        Returns:
            A ``Page[Movie]`` with the matching movies and the total count.
        """
        gateway_page = await self._gateway.find_all(
            title_filter=title_filter, limit=limit, offset=offset
        )
        return Page(
            items=[to_movie(row) for row in gateway_page.rows],
            total=gateway_page.total,
        )
