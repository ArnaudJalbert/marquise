"""Shared helpers for screening use cases."""

from __future__ import annotations

from datetime import datetime
from typing import TypeGuard, TypeVar

from marquise.domain.entities import Screening

T = TypeVar("T")


class _Unset:
    """Marker for omitted update fields."""

    __slots__ = ()


UNSET = _Unset()


def is_provided(value: T | _Unset) -> TypeGuard[T]:
    """Return whether an update input field was explicitly provided."""
    return not isinstance(value, _Unset)


def keep(existing: T, incoming: T | _Unset) -> T:
    """Return existing value when incoming value was omitted."""
    return incoming if is_provided(incoming) else existing


def reject_blank_when_provided(value: str | None, field_name: str) -> None:
    """Reject whitespace-only strings when an optional field is provided."""
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} must not be empty when provided")


def require_non_empty(value: str, field_name: str) -> None:
    """Reject empty or whitespace-only required string fields."""
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def require_timezone_aware_showtime(showtime: datetime) -> None:
    """Reject naive datetimes for screening showtimes."""
    if showtime.tzinfo is None:
        raise ValueError("showtime must be timezone-aware")


def screening_output_dict(screening: Screening) -> dict:
    """Return screening fields for a use-case-local OutputData."""
    return {
        "id": str(screening.id),
        "movie_id": str(screening.movie.id),
        "movie_title": screening.movie.title,
        "cinema_id": str(screening.cinema.id),
        "cinema_name": screening.cinema.name,
        "showtime": screening.showtime.value,
        "ticket_url": screening.ticket_url,
        "room": screening.room,
        "language": screening.language,
    }
