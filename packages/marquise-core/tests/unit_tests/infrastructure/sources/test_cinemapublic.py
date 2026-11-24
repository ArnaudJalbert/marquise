"""Tests for the Cinema Public showtime source gateway."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from marquise.infrastructure.sources.cinemapublic import (
    _extract_cinemapublic_film_detail,
    fetch_showtimes,
)

_MOVIE_URL = "https://cinemapublic.ca/en/films/kairos/"
_VENUE_ID = "#casa-d-italia"


def _jsonld_page_html(
    start_date: str,
    ticket_url: str = "https://cinemapublic.ca/tickets/1",
) -> str:
    """Build a minimal page with one JSON-LD showtime event."""
    graph = {
        "@graph": {
            "itemListElement": [
                {
                    "item": {
                        "location": {"@id": f"https://cinemapublic.ca/{_VENUE_ID}"},
                        "startDate": start_date,
                        "workPresented": {"name": "Kairos", "url": _MOVIE_URL},
                        "offers": {"url": ticket_url},
                    }
                }
            ]
        }
    }
    return (
        "<html><body>"
        f'<script type="application/ld+json">{json.dumps(graph)}</script>'
        "</body></html>"
    )


@pytest.mark.asyncio
async def test_fetch_showtimes_converts_montreal_local_to_utc() -> None:
    """A JSON-LD showtime's local Montreal time is converted to real UTC."""
    html = _jsonld_page_html("2026-07-13T17:00")

    with patch(
        "marquise.infrastructure.sources.cinemapublic._fetch",
        return_value=html,
    ):
        rows = fetch_showtimes(
            cinema_name="casa-d-italia",
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 7, 31),
        )

    # July is EDT (UTC-4): 17:00 Montreal -> 21:00 UTC.
    assert rows[0]["showtime"] == "2026-07-13T21:00:00+00:00"


@pytest.mark.asyncio
async def test_fetch_showtimes_converts_montreal_local_to_utc_in_winter() -> None:
    """Winter showtimes convert using EST (UTC-5)."""
    html = _jsonld_page_html("2026-01-13T17:00")

    with patch(
        "marquise.infrastructure.sources.cinemapublic._fetch",
        return_value=html,
    ):
        rows = fetch_showtimes(
            cinema_name="casa-d-italia",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )

    assert rows[0]["showtime"] == "2026-01-13T22:00:00+00:00"


@pytest.mark.asyncio
async def test_fetch_showtimes_repairs_malformed_ticket_host() -> None:
    """A malformed source ticket URL is repaired to the Cinema Public host."""
    html = _jsonld_page_html(
        "2026-07-13T17:00",
        ticket_url="https:///en/organisation/achat/index.cfm?RepresentationID=1",
    )

    with patch(
        "marquise.infrastructure.sources.cinemapublic._fetch",
        return_value=html,
    ):
        rows = fetch_showtimes(
            cinema_name="casa-d-italia",
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 7, 31),
        )

    assert rows[0]["ticket_url"] == (
        "https://cinemapublic.ca/en/organisation/achat/index.cfm?RepresentationID=1"
    )


def test_film_detail_unescapes_director_html_entities() -> None:
    """An entity-encoded director name is decoded before movie matching."""
    movie = {
        "@type": "Movie",
        "name": "La patrie",
        "director": {"@type": "Person", "name": "Pawe&#322; Pawlikowski"},
    }
    html = (
        "<html><body>"
        f'<script type="application/ld+json">{json.dumps({"@graph": [movie]})}</script>'
        "</body></html>"
    )

    detail = _extract_cinemapublic_film_detail(html, _MOVIE_URL)

    assert detail["directors"] == ["Paweł Pawlikowski"]
