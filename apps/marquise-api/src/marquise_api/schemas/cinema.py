"""Cinema response model for the read-only API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CinemaResponse(BaseModel):
    """A cinema in an API response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "cinema-cineplex-forum",
                    "name": "Cineplex Cinemas Forum",
                    "address": "2313 Rue Sainte-Catherine O, Montréal, QC H3H 1N2",
                    "city": "Montreal",
                    "website": "https://www.cineplex.com/theatre/cineplex-cinemas-forum",
                }
            ]
        },
    )

    id: str = Field(description="Opaque, source-provided cinema identifier.")
    name: str
    address: str | None = None
    city: str | None = None
    website: str | None = None
