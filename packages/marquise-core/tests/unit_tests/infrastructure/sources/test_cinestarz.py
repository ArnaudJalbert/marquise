"""Tests for Cine Starz showtime source gateway."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from marquise.infrastructure.sources.cinestarz import (
    CineStarzSource,
    _extract_movie_detail,
    _parse_schedule,
    fetch_showtimes,
)


def _schedule_html(
    *,
    venue_key: str = "CotedesNeiges",
    title: str = "Movie One",
    performance_id: str = "123",
) -> str:
    """Build minimal Cine Starz schedule fragment."""
    ticket_path = f"/movies/{venue_key}/MOVIE-ONE"
    return (
        f'<div class="nowPlaying__item"><a class="nowPlaying__movieLink" '
        f'href="/movie/{venue_key}/MOVIE-ONE">{title}</a>'
        '<div class="performance__item"><div class="button button--showtime '
        'button--disabled"><span>11:00 AM</span></div></div>'
        '<div class="performance__item"><a class="button button--showtime" '
        f'href="#" onclick="window.location=\'{ticket_path}/RS1-{performance_id}/'
        "ticket-selection';\"><span>2:20 PM</span></a></div>"
        '<div class="performance__item"><a class="button button--showtime" '
        f'href="#" onclick="window.location=\'{ticket_path}/RS1-456/'
        "ticket-selection';\"><span>7:05 PM</span></a></div></div>"
    )


def test_parse_schedule_extracts_enabled_showtimes() -> None:
    """Enabled ticket buttons yield UTC rows with performance IDs."""
    rows = _parse_schedule(_schedule_html(), datetime(2026, 8, 26))

    assert rows == [
        {
            "movie_title": "Movie One",
            "showtime": "2026-08-26T18:20:00+00:00",
            "identifier": "https://cinestarz.ca/movie/CotedesNeiges/MOVIE-ONE",
            "external_id": "RS1-123",
            "ticket_url": (
                "https://cinestarz.ca/movies/CotedesNeiges/MOVIE-ONE/"
                "RS1-123/ticket-selection"
            ),
            "room": None,
            "language": None,
        },
        {
            "movie_title": "Movie One",
            "showtime": "2026-08-26T23:05:00+00:00",
            "identifier": "https://cinestarz.ca/movie/CotedesNeiges/MOVIE-ONE",
            "external_id": "RS1-456",
            "ticket_url": (
                "https://cinestarz.ca/movies/CotedesNeiges/MOVIE-ONE/"
                "RS1-456/ticket-selection"
            ),
            "room": None,
            "language": None,
        },
    ]


def test_parse_schedule_accepts_ticket_paths_without_ticket_selection() -> None:
    """Cavendish's direct ticket paths yield stable performance IDs."""
    html = _schedule_html().replace("/ticket-selection", "")

    assert [
        row["external_id"] for row in _parse_schedule(html, datetime(2026, 8, 26))
    ] == [
        "RS1-123",
        "RS1-456",
    ]


def test_parse_schedule_skips_malformed_movie_and_performance_blocks() -> None:
    """Missing movie links or ticket paths do not create invalid rows."""
    html = '<div class="nowPlaying__item">broken</div>' + _schedule_html()

    assert len(_parse_schedule(html, datetime(2026, 8, 26))) == 2


def test_fetch_showtimes_fetches_each_date_and_keeps_venue_isolated() -> None:
    """Each requested day uses only supplied venue key and returns its rows."""
    calls: list[str] = []

    def fake_fetch(url: str) -> str:
        """Record request URL and return one venue-specific schedule."""
        calls.append(url)
        return _schedule_html(
            venue_key="DeluxeCavendish",
            title="Cavendish Movie",
        )

    with patch(
        "marquise.infrastructure.sources.cinestarz._fetch",
        side_effect=fake_fetch,
    ):
        rows = fetch_showtimes(
            "DeluxeCavendish", datetime(2026, 8, 26), datetime(2026, 8, 27)
        )

    assert calls == [
        "https://cinestarz.ca/theater/nowplaying?locationKey=DeluxeCavendish&date=2026-08-26",
        "https://cinestarz.ca/theater/nowplaying?locationKey=DeluxeCavendish&date=2026-08-27",
    ]
    assert len(rows) == 2
    assert {row["movie_title"] for row in rows} == {"Cavendish Movie"}
    assert all("/DeluxeCavendish/" in row["identifier"] for row in rows)
    assert all("/DeluxeCavendish/" in row["ticket_url"] for row in rows)


def test_fetch_showtimes_skips_failed_dates() -> None:
    """One failed date does not abort import."""

    def fake_fetch(url: str) -> str:
        """Fail first day and repeat same performance on second day."""
        if url.endswith("2026-08-26"):
            raise HTTPError(url, 500, "error", {}, None)  # type: ignore[arg-type]
        return _schedule_html()

    with patch(
        "marquise.infrastructure.sources.cinestarz._fetch",
        side_effect=fake_fetch,
    ):
        rows = fetch_showtimes(
            "CotedesNeiges", datetime(2026, 8, 26), datetime(2026, 8, 27)
        )

    assert [row["external_id"] for row in rows] == ["RS1-123", "RS1-456"]


def test_extract_movie_detail_reads_movie_json_ld() -> None:
    """Movie JSON-LD yields supported enrichment fields."""
    html = """<script type="application/ld+json">
{"@type":"Movie","Description":"Story","Image":"https://poster","ContentRating":"G","DateCreated":"8/14/2026"}
</script><script type="application/ld+json">
{"@type":"ItemList","ItemListElement":[{"Item":{"WorkPresented":{"Duration":"78"}}}]}
</script>"""

    assert _extract_movie_detail(html) == {
        "description": "Story",
        "duration_minutes": 78,
        "poster_url": "https://poster",
        "rating": "G",
        "release_year": 2026,
    }


def test_extract_movie_detail_ignores_invalid_or_missing_json_ld() -> None:
    """Invalid or unrelated JSON-LD yields no enrichment."""
    assert (
        _extract_movie_detail('<script type="application/ld+json">{bad}</script>') == {}
    )
    assert _extract_movie_detail('{"@type":"Movie"}') == {}


@pytest.mark.asyncio
async def test_source_fetch_movie_detail_returns_none_when_page_has_no_metadata() -> (
    None
):
    """Source converts empty parsed metadata to None."""
    with patch(
        "marquise.infrastructure.sources.cinestarz._fetch",
        return_value="<html></html>",
    ):
        assert (
            await CineStarzSource().fetch_movie_detail(
                "https://cinestarz.ca/movie/CotedesNeiges/MISSING"
            )
            is None
        )


@pytest.mark.asyncio
async def test_source_fetch_movie_detail_returns_none_on_http_error() -> None:
    """A failed movie-detail request is treated as no enrichment."""
    identifier = "https://cinestarz.ca/movie/CotedesNeiges/MISSING"

    with patch(
        "marquise.infrastructure.sources.cinestarz._fetch",
        side_effect=HTTPError(identifier, 404, "Not Found", {}, None),  # type: ignore[arg-type]
    ):
        assert await CineStarzSource().fetch_movie_detail(identifier) is None
