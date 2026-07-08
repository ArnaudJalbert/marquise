"""Pydantic response models for the read-only API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CinemaResponse(BaseModel):
    """A cinema in an API response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    address: str | None = None
    city: str | None = None
    website: str | None = None


class MovieResponse(BaseModel):
    """A movie in an API response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    release_year: int | None = None
    directors: tuple[str, ...] | None = None
    cast: tuple[str, ...] | None = None
    duration_minutes: int | None = None
    description: str | None = None
    poster_url: str | None = None
    trailer_url: str | None = None
    genres: tuple[str, ...] | None = None
    original_title: str | None = None
    rating: str | None = None
    origin_countries: tuple[str, ...] | None = None


class ScreeningResponse(BaseModel):
    """A single screening in an API response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    movie_id: str
    movie_title: str
    showtime: str
    ticket_url: str | None = None
    room: str | None = None
    language: str | None = None


class CinemaShowtimesResponse(BaseModel):
    """A cinema with its screenings in a date range."""

    model_config = ConfigDict(from_attributes=True)

    cinema_id: str
    cinema_name: str
    screenings: list[ScreeningResponse]
