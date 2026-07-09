"""Supabase repository implementation of ScreeningRepository.

Adapts a ``ScreeningGateway`` (infrastructure) into the ``ScreeningRepository``
interface (application).  No SQL, no asyncpg — pure entity mapping.
"""

from __future__ import annotations

from datetime import UTC, datetime

from marquise.application.exceptions import ScreeningAlreadyExistsError
from marquise.application.repositories import Page, ScreeningRepository
from marquise.domain.entities import Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)
from marquise.interface_adapters.repositories.protocols.base import GatewayError
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningGateway,
)
from marquise.interface_adapters.repositories.supabase._utils import (
    dict_to_cinema,
    extract_prefixed,
)


def _parse_datetime(value: datetime) -> datetime:
    """Normalize a gateway datetime to a timezone-aware UTC datetime.

    The screening gateway always returns ``datetime`` objects from asyncpg.
    Naive values are assumed to be in UTC and made timezone-aware.

    Args:
        value: A datetime object returned by the gateway.

    Returns:
        A timezone-aware datetime.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _dict_to_movie(data: dict) -> Movie:
    """Convert a prefixed movie dict into a Movie entity.

    Args:
        data: A dict with movie keys (``id``, ``title``, etc.).

    Returns:
        A new Movie entity.
    """
    raw_directors = data.get("directors")
    directors = tuple(raw_directors.split(",")) if raw_directors else None
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


class SupabaseScreeningRepository(ScreeningRepository):
    """Screening repository backed by a Supabase PostgreSQL database.

    Parameters
    ----------
    gateway:
        A data gateway that implements ``ScreeningGateway``.
    """

    def __init__(self, gateway: ScreeningGateway) -> None:
        self._gateway = gateway

    async def save(self, screening: Screening) -> tuple[Screening, bool]:
        """Persist a screening via the gateway and return the mapped entity.

        Args:
            screening: The screening domain entity to save.

        Returns:
            A tuple of (saved_screening, was_inserted).

        Raises:
            ScreeningAlreadyExistsError: If ``external_id`` collides with a
                row that has a different (cinema_id, movie_id, showtime).
        """
        try:
            outcome = await self._gateway.save(
                screening_id=str(screening.id),
                movie_id=str(screening.movie.id),
                cinema_id=str(screening.cinema.id),
                showtime=screening.showtime.value,
                external_id=screening.external_id,
                ticket_url=screening.ticket_url,
                room=screening.room,
                language=screening.language,
            )
        except GatewayError as exc:
            raise ScreeningAlreadyExistsError(str(exc)) from exc
        data = outcome.row
        was_inserted = outcome.inserted
        saved = Screening(
            id=ScreeningId(value=data["id"]),
            movie=screening.movie,
            cinema=screening.cinema,
            showtime=Showtime(value=_parse_datetime(data["showtime"])),
            external_id=data.get("external_id"),
            ticket_url=data.get("ticket_url"),
            room=data.get("room"),
            language=data.get("language"),
        )
        return saved, was_inserted

    async def update(self, screening: Screening) -> Screening | None:
        """Update optional fields on an existing screening.

        Args:
            screening: The screening with updated optional fields.

        Returns:
            The updated screening entity, or None if no match exists.
        """
        data = await self._gateway.update(
            cinema_id=str(screening.cinema.id),
            movie_id=str(screening.movie.id),
            showtime=screening.showtime.value,
            external_id=screening.external_id,
            ticket_url=screening.ticket_url,
            room=screening.room,
            language=screening.language,
        )
        if data is None:
            return None
        return Screening(
            id=ScreeningId(value=data["id"]),
            movie=screening.movie,
            cinema=screening.cinema,
            showtime=Showtime(value=_parse_datetime(data["showtime"])),
            external_id=data.get("external_id"),
            ticket_url=data.get("ticket_url"),
            room=data.get("room"),
            language=data.get("language"),
        )

    async def find_by_id(self, screening_id: ScreeningId) -> Screening | None:
        """Retrieve a screening by ID.

        Args:
            screening_id: The unique identifier of the screening.

        Returns:
            The matching screening entity, or None if not found.
        """
        data = await self._gateway.find_by_id(screening_id=str(screening_id))
        return self._to_entity(data) if data is not None else None

    async def find_by_cinema_and_date_range(
        self,
        cinema_id: CinemaId,
        start_date: datetime,
        end_date: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[Screening]:
        """Find screenings for a cinema within a date range, paginated.

        Args:
            cinema_id: The cinema to filter by.
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).
            limit: Max number of screenings to return. If None, all matching
                screenings are returned unbounded.
            offset: Number of matching screenings to skip before returning
                results.

        Returns:
            A ``Page[Screening]`` with the matching screenings and the total
            count.
        """
        gateway_page = await self._gateway.find_by_cinema_and_date_range(
            cinema_id=str(cinema_id),
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        return Page(
            items=[self._to_entity(row) for row in gateway_page.rows],
            total=gateway_page.total,
        )

    @staticmethod
    def _to_entity(data: dict) -> Screening:
        """Map a raw gateway dict to a Screening domain entity.

        Args:
            data: The dict returned by the gateway (with joined movie and
                cinema data prefixed with ``movie__`` and ``cinema__``).

        Returns:
            A new Screening entity populated with the dict values.
        """
        movie = _dict_to_movie(extract_prefixed(data, "movie__"))
        cinema = dict_to_cinema(extract_prefixed(data, "cinema__"))
        return Screening(
            id=ScreeningId(value=data["id"]),
            movie=movie,
            cinema=cinema,
            showtime=Showtime(value=_parse_datetime(data["showtime"])),
            external_id=data.get("external_id"),
            ticket_url=data.get("ticket_url"),
            room=data.get("room"),
            language=data.get("language"),
        )
