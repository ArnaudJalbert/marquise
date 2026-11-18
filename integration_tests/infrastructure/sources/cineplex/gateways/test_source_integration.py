"""Offline HTTP integration tests for the Cineplex source."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from marquise.infrastructure.sources.cineplex.gateways import source as cineplex


@pytest.mark.asyncio
async def test_fetch_showtimes_filters_sessions_and_preserves_ticket_metadata(
    local_http: tuple[str, dict[str, tuple[bytes, str]], list[tuple[str, str | None]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fetch a local API response and retain only sessions in the UTC window."""
    base_url, routes, requests = local_http
    monkeypatch.setattr(cineplex, "SHOWTIMES_URL", f"{base_url}/showtimes")
    monkeypatch.setattr(cineplex, "_discover_subscription_key", lambda: "fixture-key")
    routes["/showtimes?LocationId=9172"] = (
        json.dumps(
            [
                {
                    "theatreId": 9172,
                    "dates": [
                        {
                            "movies": [
                                {
                                    "name": "Fixture Film",
                                    "filmUrl": "fixture-film",
                                    "language": "French",
                                    "subtitleLanguage": "English",
                                    "experiences": [
                                        {
                                            "experienceTypes": ["IMAX", "3D"],
                                            "sessions": [
                                                {
                                                    "showStartDateTimeUtc": (
                                                        "2026-02-10T20:00:00Z"
                                                    ),
                                                    "vistaSessionId": 401,
                                                    "ticketingRedesignUrl": "https://tickets.example/401",
                                                    "auditorium": "Screen 2",
                                                },
                                                {
                                                    "showStartDateTimeUtc": (
                                                        "2026-02-12T20:00:00Z"
                                                    ),
                                                    "vistaSessionId": 402,
                                                },
                                            ],
                                        }
                                    ],
                                }
                            ]
                        }
                    ],
                }
            ]
        ).encode(),
        "application/json",
    )

    results = await cineplex.CineplexSource().fetch_showtimes(
        location_id=9172,
        start_date=datetime(2026, 2, 10, tzinfo=UTC),
        end_date=datetime(2026, 2, 11, tzinfo=UTC),
    )

    assert results == [
        {
            "movie_title": "Fixture Film",
            "showtime": "2026-02-10T20:00:00+00:00",
            "identifier": "fixture-film",
            "external_id": "401",
            "ticket_url": "https://tickets.example/401",
            "room": "Screen 2",
            "language": "French (English subtitles)",
            "experience": "IMAX+3D",
        }
    ]
    assert requests == [("/showtimes?LocationId=9172", "fixture-key")]


@pytest.mark.asyncio
async def test_fetch_movie_detail_parses_next_data_from_local_page(
    local_http: tuple[str, dict[str, tuple[bytes, str]], list[tuple[str, str | None]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fetch a local Next.js page and extract its film metadata."""
    base_url, routes, requests = local_http
    monkeypatch.setattr(cineplex, "MOVIE_DETAIL_TPL", f"{base_url}/movie/{{slug}}")
    movie = {
        "props": {
            "pageProps": {
                "movieDetails": {
                    "director": "Ada Example, Bo Example",
                    "starring": "Cam Example, Dee Example",
                    "genres": ["Drama", "Comedy"],
                    "ratings": [{"description": "PG"}],
                    "synopsis": "<p>A story &amp; another.</p>",
                    "runtimeInMinutes": 99,
                    "releaseDate": "2026-02-06T00:00:00Z",
                    "largePosterImageUrl": "https://images.example/poster.jpg",
                }
            }
        }
    }
    routes["/movie/fixture-film"] = (
        (
            '<script id="__NEXT_DATA__" type="application/json">'
            f"{json.dumps(movie)}</script>"
        ).encode(),
        "text/html",
    )

    detail = await cineplex.CineplexSource().fetch_movie_detail("fixture-film")

    assert detail == {
        "description": "A story & another.",
        "directors": ["Ada Example", "Bo Example"],
        "cast": ["Cam Example", "Dee Example"],
        "duration_minutes": 99,
        "release_year": 2026,
        "origin_countries": None,
        "poster_url": "https://images.example/poster.jpg",
        "trailer_url": None,
        "genres": ["Drama", "Comedy"],
        "rating": "PG",
        "original_title": None,
    }
    assert requests == [("/movie/fixture-film", None)]
