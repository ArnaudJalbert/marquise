"""Offline HTTP integration tests for the CinemaCinema source."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from marquise.infrastructure.sources.cinemacinema.gateways import source as cinema


def _svelte_response(root: dict[str, Any]) -> bytes:
    """Encode minimal SvelteKit devalue data with references for numeric fields."""
    return json.dumps(
        {"nodes": [None, {"data": [root, 1, 2, 3, 510, 511, 95, 2026]}]}
    ).encode()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cinema_name", "expected"),
    [
        (
            "du-musee",
            [
                {
                    "movie_title": "Museum Film",
                    "showtime": "2026-02-11T00:30:00+00:00",
                    "identifier": "museum-film",
                    "external_id": "510",
                    "ticket_url": "https://billetterie.cinemadumusee.com/FR/Film-achats.awp?P1=510&P2=",
                    "room": "2",
                    "language": "VOF",
                },
                {
                    "movie_title": "Museum Film",
                    "showtime": "2026-02-12T01:15:00+00:00",
                    "identifier": "museum-film",
                    "external_id": "511",
                    "ticket_url": "https://billetterie.cinemadumusee.com/FR/Film-achats.awp?P1=511&P2=",
                    "room": None,
                    "language": "VOSTA",
                },
            ],
        ),
        (
            "du-parc",
            [
                {
                    "movie_title": "Park Film",
                    "showtime": "2026-02-11T00:30:00+00:00",
                    "identifier": "park-film",
                    "external_id": "510",
                    "ticket_url": "https://billetterie.cinemaduparc.com/FR/Film-achats.awp?P1=510&P2=",
                    "room": "1",
                    "language": "VOA",
                }
            ],
        ),
    ],
)
async def test_fetch_showtimes_uses_local_dated_schedule_and_filters_cinema(
    cinema_name: str,
    expected: list[dict],
    local_http: tuple[str, dict[str, tuple[bytes, str]], list[tuple[str, str | None]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fetch two local dates, normalize Montreal time, and select the cinema."""
    base_url, routes, requests = local_http
    monkeypatch.setattr(cinema, "SCHEDULE_URL", f"{base_url}/schedule/__data.json")
    routes["/schedule/__data.json"] = (
        _svelte_response(
            {
                "cmDates": ["2026-02-10T00:00:00Z", "2026-02-11T00:00:00Z"],
                "filmsRepresentations": [
                    {
                        "cinema_id": 3,
                        "slug": "museum-film",
                        "titre": "Museum Film",
                        "representations": [
                            {
                                "representation_id": 4,
                                "representation_date": "2026-02-10T00:00:00Z",
                                "heure_debut": "7:30 PM",
                                "salle": 2,
                                "version": "VOF",
                            }
                        ],
                    },
                    {
                        "cinema_id": 2,
                        "slug": "park-film",
                        "titre": "Park Film",
                        "representations": [
                            {
                                "representation_id": 4,
                                "representation_date": "2026-02-10T00:00:00Z",
                                "heure_debut": "19:30",
                                "salle": 1,
                                "version": "VOA",
                            }
                        ],
                    },
                ],
            }
        ),
        "application/json",
    )
    routes["/schedule/__data.json?date=2026-02-11"] = (
        _svelte_response(
            {
                "filmsRepresentations": [
                    {
                        "cinema_id": 3,
                        "slug": "museum-film",
                        "titre": "Museum Film",
                        "representations": [
                            {
                                "representation_id": 5,
                                "representation_date": "2026-02-11T00:00:00Z",
                                "heure_debut": "20:15",
                                "version": "VOSTA",
                            }
                        ],
                    }
                ]
            }
        ),
        "application/json",
    )

    results = await cinema.CinemaCinemaSource().fetch_showtimes(
        cinema_name=cinema_name,
        start_date=datetime(2026, 2, 10, tzinfo=UTC),
        end_date=datetime(2026, 2, 11, tzinfo=UTC),
    )

    assert results == expected
    assert requests == [
        ("/schedule/__data.json", None),
        ("/schedule/__data.json?date=2026-02-11", None),
    ]


@pytest.mark.asyncio
async def test_fetch_movie_detail_parses_local_svelte_data(
    local_http: tuple[str, dict[str, tuple[bytes, str]], list[tuple[str, str | None]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fetch a local film page and extract its devalue metadata."""
    base_url, routes, requests = local_http
    monkeypatch.setattr(
        cinema, "FILM_DETAIL_TPL", f"{base_url}/films/{{slug}}/__data.json"
    )
    routes["/films/museum-film/__data.json"] = (
        _svelte_response(
            {
                "cmFilmCurrent": {
                    "realisateur": "Ada Example, Bo Example",
                    "acteurs": "Cam Example, Dee Example",
                    "genre1": "Drama",
                    "genre2": "Mystery",
                    "origine1": "Canada",
                    "synopsis": "<p>A story &amp; another.</p>",
                    "duree": 6,
                    "annee": 7,
                    "poster_url": "https://images.example/museum.jpg",
                    "bande_annonce_url": "https://videos.example/trailer",
                    "classment": "G",
                    "original_title": "Original Film",
                }
            }
        ),
        "application/json",
    )

    detail = await cinema.CinemaCinemaSource().fetch_movie_detail("museum-film")

    assert detail == {
        "description": "A story & another.",
        "directors": ["Ada Example", "Bo Example"],
        "cast": ["Cam Example", "Dee Example"],
        "duration_minutes": 95,
        "release_year": 2026,
        "origin_countries": ["Canada"],
        "poster_url": "https://images.example/museum.jpg",
        "trailer_url": "https://videos.example/trailer",
        "genres": ["Drama", "Mystery"],
        "rating": "G",
        "original_title": "Original Film",
    }
    assert requests == [("/films/museum-film/__data.json", None)]
