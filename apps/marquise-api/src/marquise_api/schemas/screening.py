"""Screening request and response models for public reads and protected writes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)
from pydantic.json_schema import SkipJsonSchema


def _validate_ticket_url(value: str) -> str:
    """Validate HTTP(S) syntax locally without normalizing or fetching the URL."""
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("ticket_url must be an absolute HTTP(S) URL with a hostname")
    HttpUrl(value)
    return value


TicketUrl = Annotated[
    str,
    AfterValidator(_validate_ticket_url),
    Field(
        description="Absolute HTTP or HTTPS ticket URL with a hostname; never fetched."
    ),
]


class CreateScreeningRequest(BaseModel):
    """Input for creating a screening with existing parents."""

    model_config = ConfigDict(extra="forbid")

    movie_id: str
    cinema_id: str
    showtime: AwareDatetime
    ticket_url: TicketUrl | None = None
    room: str | None = None
    language: str | None = None
    external_id: str | None = None


class UpdateScreeningRequest(BaseModel):
    """Partial edit: omit to keep; null clears optional metadata only."""

    model_config = ConfigDict(extra="forbid")

    movie_id: str | SkipJsonSchema[None] = Field(
        default=None, description="Omit to keep; null is invalid."
    )
    cinema_id: str | SkipJsonSchema[None] = Field(
        default=None, description="Omit to keep; null is invalid."
    )
    showtime: AwareDatetime | SkipJsonSchema[None] = Field(
        default=None, description="Timezone-aware timestamp; omit to keep, never null."
    )
    ticket_url: TicketUrl | None = None
    room: str | None = None
    language: str | None = None
    external_id: str | None = None

    @field_validator("movie_id", "cinema_id", "showtime")
    @classmethod
    def reject_null_identity(cls, value: str | datetime | None) -> str | datetime:
        """Only optional metadata can be explicitly cleared."""
        if value is None:
            raise ValueError("Identity fields cannot be null")
        return value


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
