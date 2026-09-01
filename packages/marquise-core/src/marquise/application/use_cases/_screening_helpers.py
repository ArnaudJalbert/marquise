"""Shared helpers for screening use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar, cast

from marquise.domain.entities import Screening

T = TypeVar("T")
UNSET: object = object()


@dataclass(frozen=True, slots=True)
class ScreeningDetailOutput:
    """Screening fields returned by create, get, and update."""

    id: str
    movie_id: str
    movie_title: str
    cinema_id: str
    cinema_name: str
    showtime: datetime
    ticket_url: str | None = None
    room: str | None = None
    language: str | None = None


def is_provided(value: object) -> bool:
    """Return whether an update input field was explicitly provided."""
    return value is not UNSET


def keep(existing: T, incoming: object) -> T:
    """Return ``existing`` when ``incoming`` was omitted, else ``incoming``."""
    return existing if not is_provided(incoming) else cast(T, incoming)


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


def screening_output_data(screening: Screening) -> ScreeningDetailOutput:
    """Build screening output data from a domain entity."""
    return ScreeningDetailOutput(
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
