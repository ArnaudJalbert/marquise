"""Shared mappers from gateway rows to entities and read models."""

from __future__ import annotations

from datetime import UTC, datetime

from marquise.application.readers import ScreeningReader
from marquise.domain.entities import Cinema, Movie
from marquise.domain.value_objects import CinemaId, MovieId


def extract_prefixed(data: dict, prefix: str) -> dict:
    """Extract keys with a given prefix into a new dict, stripping the prefix.

    Args:
        data: The dict to extract from.
        prefix: The prefix to match.

    Returns:
        A new dict with the prefix stripped from matching keys.
    """
    return {k[len(prefix) :]: v for k, v in data.items() if k.startswith(prefix)}


def to_cinema(data: dict) -> Cinema:
    """Convert gateway cinema data into a Cinema entity.

    Args:
        data: A dict with ``id``, ``name``, ``address``, ``city``,
            ``website`` keys.

    Returns:
        A new Cinema entity.
    """
    return Cinema(
        id=CinemaId(value=data["id"]),
        name=data["name"],
        address=data["address"],
        city=data["city"],
        website=data["website"],
    )


def _split_comma_separated_values(value: str | None) -> tuple[str, ...] | None:
    return tuple(value.split(",")) if value else None


def to_movie(data: dict) -> Movie:
    """Convert gateway movie data into a Movie entity.

    Args:
        data: The gateway row with movie columns.

    Returns:
        The matching Movie entity.
    """
    return Movie(
        id=MovieId(value=data["id"]),
        title=data["title"],
        release_year=data.get("release_year"),
        directors=_split_comma_separated_values(data.get("directors")),
        cast=_split_comma_separated_values(data.get("cast_members")),
        duration_minutes=data.get("duration_minutes"),
        description=data.get("description"),
        poster_url=data.get("poster_url"),
        trailer_url=data.get("trailer_url"),
        genres=_split_comma_separated_values(data.get("genres")),
        original_title=data.get("original_title"),
        rating=data.get("rating"),
        origin_countries=_split_comma_separated_values(data.get("origin_countries")),
        tmdb_id=data.get("tmdb_id"),
        tmdb_rating=data.get("tmdb_rating"),
        tmdb_vote_count=data.get("tmdb_vote_count"),
    )


def to_aware_utc(value: datetime) -> datetime:
    """Return a datetime as a timezone-aware UTC datetime.

    Args:
        value: A naive datetime holding UTC, or an aware datetime.

    Returns:
        An aware UTC datetime. Aware input shifts to the same UTC instant.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_screening_data(row: dict) -> ScreeningReader.ScreeningData:
    """Map a screening display row without hydrating movie or cinema entities.

    Args:
        row: The gateway row with screening display columns.

    Returns:
        The matching screening read model.
    """
    return ScreeningReader.ScreeningData(
        id=row["id"],
        movie_id=row["movie_id"],
        movie_title=row["movie_title"],
        cinema_id=row["cinema_id"],
        cinema_name=row["cinema_name"],
        showtime=to_aware_utc(row["showtime"]),
        ticket_url=row.get("ticket_url"),
        room=row.get("room"),
        language=row.get("language"),
    )
