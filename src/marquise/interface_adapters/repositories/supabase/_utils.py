"""Shared utility functions for Supabase repository implementations."""

from __future__ import annotations

from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


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
