"""Immutable history of a screening change."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from marquise.domain.entities.movie import Movie
from marquise.domain.entities.screening import Screening


@dataclass(frozen=True, slots=True)
class ScreeningSnapshot:
    """Selected persisted screening values, independent of later entity changes."""

    id: str
    movie_id: str
    cinema_id: str
    showtime: datetime
    external_id: str | None
    ticket_url: str | None
    room: str | None
    language: str | None

    @classmethod
    def from_screening(cls, screening: Screening) -> "ScreeningSnapshot":
        """Capture the selected values of a screening."""
        return cls(
            id=str(screening.id),
            movie_id=str(screening.movie.id),
            cinema_id=str(screening.cinema.id),
            showtime=screening.showtime.value,
            external_id=screening.external_id,
            ticket_url=screening.ticket_url,
            room=screening.room,
            language=screening.language,
        )


@dataclass(frozen=True, slots=True)
class MovieSnapshot:
    """Movie values retained when orphan cleanup removes a movie."""

    id: str
    title: str
    release_year: int | None
    directors: tuple[str, ...] | None
    cast: tuple[str, ...] | None
    duration_minutes: int | None
    description: str | None
    poster_url: str | None
    trailer_url: str | None
    genres: tuple[str, ...] | None
    original_title: str | None
    rating: str | None
    origin_countries: tuple[str, ...] | None

    @classmethod
    def from_movie(cls, movie: Movie) -> "MovieSnapshot":
        """Capture movie metadata without retaining a mutable entity."""
        return cls(
            id=str(movie.id),
            title=movie.title,
            release_year=movie.release_year,
            directors=movie.directors,
            cast=movie.cast,
            duration_minutes=movie.duration_minutes,
            description=movie.description,
            poster_url=movie.poster_url,
            trailer_url=movie.trailer_url,
            genres=movie.genres,
            original_title=movie.original_title,
            rating=movie.rating,
            origin_countries=movie.origin_countries,
        )


@dataclass(frozen=True, slots=True)
class ScreeningAuditRecord:
    """Attributable history constructed by an application use case."""

    account: str
    key: str
    operation: Literal["create", "update", "delete"]
    target: str
    timestamp: datetime
    reason: str
    before: ScreeningSnapshot | None
    after: ScreeningSnapshot | None
    removed_movie: MovieSnapshot | None = None

    def __post_init__(self) -> None:
        """Reject ambiguous timestamps on application-generated history."""
        if self.timestamp.utcoffset() is None:
            raise ValueError("Audit timestamp must be timezone-aware")
