"""Shared utility functions for Supabase repository implementations."""

from __future__ import annotations

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


def dict_to_cinema(data: dict) -> Cinema:
    """Convert a prefixed cinema dict into a Cinema entity.

    Args:
        data: A dict with ``id``, ``name``, ``address``, ``city``,
            ``website`` keys.

    Returns:
        A new Cinema entity.
    """
    return Cinema(
        id=CinemaId(value=data["id"]),
        name=data["name"],
        address=data.get("address"),
        city=data.get("city"),
        website=data.get("website"),
    )


def _split_comma_separated_values(value: str | None) -> tuple[str, ...] | None:
    return tuple(value.split(",")) if value else None


def dict_to_movie(data: dict) -> Movie:
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
