"""Screening response model for the read-only API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScreeningResponse(BaseModel):
    """A single screening in an API response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "screening-123456",
                    "movie_id": "movie-dune-part-two",
                    "movie_title": "Dune: Part Two",
                    "cinema_id": "cinema-cineplex-forum",
                    "cinema_name": "Cineplex Forum",
                    "showtime": "2026-07-11T19:30:00+00:00",
                    "ticket_url": "https://www.cineplex.com/tickets/123456",
                    "room": "Salle 4",
                    "language": "V.O.",
                }
            ]
        },
    )

    id: str = Field(description="Opaque, source-provided screening identifier.")
    movie_id: str
    movie_title: str
    cinema_id: str
    cinema_name: str
    showtime: datetime = Field(
        description="ISO 8601 timestamp of the screening, in UTC."
    )
    ticket_url: str | None = None
    room: str | None = None
    language: str | None = None
