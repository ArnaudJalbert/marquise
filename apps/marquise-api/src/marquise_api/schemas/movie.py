"""Movie response model for the read-only API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MovieResponse(BaseModel):
    """A movie in an API response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "movie-dune-part-two",
                    "title": "Dune: Part Two",
                    "release_year": 2024,
                    "directors": ["Denis Villeneuve"],
                    "cast": ["Timothée Chalamet", "Zendaya"],
                    "duration_minutes": 166,
                    "description": (
                        "Paul Atreides unites with Chani and the Fremen while "
                        "seeking revenge against the conspirators who "
                        "destroyed his family."
                    ),
                    "poster_url": "https://example.com/posters/dune-part-two.jpg",
                    "trailer_url": "https://www.youtube.com/watch?v=Way9Dexny3w",
                    "genres": ["Science Fiction", "Adventure"],
                    "original_title": "Dune: Part Two",
                    "rating": "13+",
                    "origin_countries": ["US"],
                }
            ]
        },
    )

    id: str = Field(description="Opaque, source-provided movie identifier.")
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
