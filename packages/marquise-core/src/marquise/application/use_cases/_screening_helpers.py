"""Shared helpers for screening use cases."""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar, cast

from marquise.domain.entities import Screening

_OutputData = TypeVar("_OutputData")
UNSET: object = object()


def is_provided(value: object) -> bool:
    """Return whether an update input field was explicitly provided."""
    return value is not UNSET


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


def as_provided_datetime(value: datetime | object) -> datetime:
    """Narrow a provided update field to ``datetime`` after an ``is_provided`` check."""
    return cast(datetime, value)


def as_provided_optional_str(value: str | None | object) -> str | None:
    """Narrow a provided optional string field after an ``is_provided`` check."""
    return cast(str | None, value)


def screening_output_data(
    output_data_cls: type[_OutputData],
    screening: Screening,
) -> _OutputData:
    """Build a screening use-case OutputData instance from a domain entity."""
    return output_data_cls(
        id=str(screening.id),
        movie_id=str(screening.movie.id),
        movie_title=screening.movie.title,
        cinema_id=str(screening.cinema.id),
        cinema_name=screening.cinema.name,
        showtime=screening.showtime.value,
        ticket_url=screening.ticket_url,
        room=screening.room,
        language=screening.language,
    )
