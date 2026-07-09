"""Tests for the Cinémathèque québécoise showtime source gateway."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from marquise.infrastructure.sources.cinematheque.gateways.source import (
    CinemathequeSource,
    _extract_available_dates,
    _extract_movie_data,
    _parse_movie_data,
    _parse_runtime,
    _split_title_and_language,
    fetch_showtimes,
)


def _schedule_html(movie_data: dict, option_dates: list[str] | None = None) -> str:
    """Build a minimal schedule page around a ``gMovieData`` payload.

    Mirrors the real page's structure closely enough for the regexes in
    ``source.py`` to extract from: a ``var gMovieData = {...};`` script
    block followed immediately by ``</script>``, and, further down, a
    ``<select id="calendar">`` with one ``<option>`` per other available
    date.
    """
    options = "".join(
        f'<option value="{d}">Some Day, {d}</option>' for d in (option_dates or [])
    )
    return (
        "<html><body>"
        f"<script> var gMovieData = {json.dumps(movie_data)}</script>"
        '<script> var gDisableCodes = "";</script>'
        f'<select id="calendar" name="schdate">{options}</select>'
        "</body></html>"
    )


def _film(
    code: str,
    title: str,
    *,
    room: str = "SALLE 1",
    start_time: str = "19:00",
    sch_date_str: str = "2026-07-09",
    perf_ix: str = "1000",
    synopsis: list[str] | None = None,
    run_time_str: str = "1 hr 30 min",
    rating_reason: str = "Pour tout public",
    poster_file: str = "../files-theatre-cinematheque/images/posters/x.png",
) -> dict:
    """Build a minimal ``gMovieData`` entry for one film."""
    return {
        "code": code,
        "title": title,
        "ratingReason": rating_reason,
        "runTimeStr": run_time_str,
        "synopsis": synopsis if synopsis is not None else [],
        "posterFile": poster_file,
        "schAuds": {
            "1": {
                "name": room,
                "schPerfsReserved": {},
                "schPerfsGeneral": {
                    start_time: {
                        "schDateStr": sch_date_str,
                        "startTime": start_time,
                        "perfIx": perf_ix,
                        "linkStr": (
                            f"?schdate={sch_date_str}&film={code}"
                            f"&aud=1&ptime={start_time}&ptype=G"
                        ),
                    }
                },
            }
        },
    }


def test_extract_movie_data_parses_embedded_json() -> None:
    """gMovieData JSON blob is extracted and parsed from the page HTML."""
    movie_data = {"123": _film("123", "A Movie")}
    html = _schedule_html(movie_data)

    result = _extract_movie_data(html)

    assert result == movie_data


def test_extract_movie_data_returns_empty_dict_when_absent() -> None:
    """A page with no schedule (e.g. out-of-range date) yields {}."""
    html = "<html><body>No schedule here</body></html>"

    assert _extract_movie_data(html) == {}


def test_extract_available_dates_finds_all_option_values() -> None:
    """Every <option value=YYYY-MM-DD> in the calendar select is returned."""
    html = _schedule_html({}, option_dates=["2026-07-10", "2026-07-11"])

    assert _extract_available_dates(html) == ["2026-07-10", "2026-07-11"]


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Romería (VOSTF)", ("Romería", "VOSTF")),
        ("Santo vs. the Evil Brain (VOSTA)", ("Santo vs. the Evil Brain", "VOSTA")),
        ("Le chant des forêts (VOF)", ("Le chant des forêts", "VOF")),
        ("A Movie With No Marker", ("A Movie With No Marker", None)),
    ],
)
def test_split_title_and_language_strips_trailing_marker(
    title: str, expected: tuple[str, str | None]
) -> None:
    """A trailing parenthetical version marker is stripped off the title."""
    assert _split_title_and_language(title) == expected


@pytest.mark.parametrize(
    ("run_time_str", "expected"),
    [
        ("1 hr 27 min", 87),
        ("45 min", 45),
        ("2 hr", 120),
        (None, None),
        ("", None),
    ],
)
def test_parse_runtime(run_time_str: str | None, expected: int | None) -> None:
    """Runtime strings are converted to minutes."""
    assert _parse_runtime(run_time_str) == expected


def test_parse_movie_data_builds_showtime_rows() -> None:
    """A gMovieData dict flattens into one row per performance."""
    movie_data = {
        "123": _film(
            "123",
            "Romería (VOSTF)",
            room="SALLE 2",
            start_time="14:00",
            sch_date_str="2026-07-09",
            perf_ix="14093",
        )
    }

    rows = _parse_movie_data(movie_data, "2026-07-09")

    assert rows == [
        {
            "movie_title": "Romería",
            "showtime": "2026-07-09T14:00",
            "identifier": "2026-07-09|123",
            "external_id": "14093",
            "ticket_url": (
                "https://omniwebticketing6.com/cinematheque/"
                "?schdate=2026-07-09&film=123&aud=1&ptime=14:00&ptype=G"
            ),
            "room": "SALLE 2",
            "language": "VOSTF",
        }
    ]


def test_parse_movie_data_skips_films_without_title() -> None:
    """A film entry with a blank title is dropped, not surfaced as a row."""
    movie_data = {"123": _film("123", "  ")}

    assert _parse_movie_data(movie_data, "2026-07-09") == []


@pytest.mark.asyncio
async def test_fetch_showtimes_combines_today_and_future_dates() -> None:
    """Today's page bootstraps the date list; other in-range dates are fetched."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_html = _schedule_html(
        {"1": _film("1", "Today's Movie", sch_date_str=today, start_time="18:00")},
        option_dates=["2026-12-25"],
    )

    def fake_fetch(url: str) -> str:
        if f"schdate={today}" in url:
            return today_html
        if "schdate=2026-12-25" in url:
            return _schedule_html(
                {
                    "2": _film(
                        "2",
                        "Future Movie",
                        sch_date_str="2026-12-25",
                        start_time="20:00",
                    )
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    with patch(
        "marquise.infrastructure.sources.cinematheque.gateways.source._fetch",
        side_effect=fake_fetch,
    ):
        rows = fetch_showtimes(end_date=datetime(2026, 12, 31))

    titles = {row["movie_title"] for row in rows}
    assert titles == {"Today's Movie", "Future Movie"}


@pytest.mark.asyncio
async def test_fetch_showtimes_excludes_out_of_range_dates() -> None:
    """Dates outside the requested [start, end] window are not fetched."""
    today_html = _schedule_html({}, option_dates=["2026-12-25"])

    calls: list[str] = []

    def fake_fetch(url: str) -> str:
        calls.append(url)
        return today_html

    with patch(
        "marquise.infrastructure.sources.cinematheque.gateways.source._fetch",
        side_effect=fake_fetch,
    ):
        fetch_showtimes(
            start_date=datetime.now(),
            end_date=datetime.now(),
        )

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_fetch_showtimes_accepts_timezone_aware_range() -> None:
    """Timezone-aware start/end (as ImportScreeningsUseCase passes) don't crash.

    Regression test: comparing a naive date parsed from the schedule page
    against a tz-aware start/end datetime used to raise
    ``TypeError: can't compare offset-naive and offset-aware datetimes``.
    """
    today_html = _schedule_html({}, option_dates=["2026-12-25"])

    with patch(
        "marquise.infrastructure.sources.cinematheque.gateways.source._fetch",
        return_value=today_html,
    ):
        rows = fetch_showtimes(
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC) + timedelta(days=7),
        )

    assert rows == []


@pytest.mark.asyncio
async def test_source_fetch_showtimes_delegates_to_module_function() -> None:
    """CinemathequeSource.fetch_showtimes wraps the module-level function."""
    html = _schedule_html({})

    with patch(
        "marquise.infrastructure.sources.cinematheque.gateways.source._fetch",
        return_value=html,
    ):
        source = CinemathequeSource()
        rows = await source.fetch_showtimes(
            start_date=datetime.now(), end_date=datetime.now()
        )

    assert rows == []


@pytest.mark.asyncio
async def test_fetch_movie_detail_returns_enrichment_from_matching_film() -> None:
    """fetch_movie_detail re-fetches the identifier's date and finds the film."""
    movie_data = {
        "123": _film(
            "123",
            "Romería (VOSTF)",
            synopsis=["Une chronique", "familiale."],
            run_time_str="1 hr 55 min",
            rating_reason="Pour tout public",
            poster_file="../files-theatre-cinematheque/images/posters/romeria.png",
        )
    }
    html = _schedule_html(movie_data)

    with patch(
        "marquise.infrastructure.sources.cinematheque.gateways.source._fetch",
        return_value=html,
    ):
        source = CinemathequeSource()
        result = await source.fetch_movie_detail("2026-07-09|123")

    assert result == {
        "description": "Une chronique familiale.",
        "duration_minutes": 115,
        "rating": "Pour tout public",
        "poster_url": (
            "https://omniwebticketing6.com/files-theatre-cinematheque/"
            "images/posters/romeria.png"
        ),
    }


@pytest.mark.asyncio
async def test_fetch_movie_detail_returns_none_for_unknown_film_code() -> None:
    """No matching film code on that date's page yields None."""
    html = _schedule_html({"999": _film("999", "Some Other Movie")})

    with patch(
        "marquise.infrastructure.sources.cinematheque.gateways.source._fetch",
        return_value=html,
    ):
        source = CinemathequeSource()
        result = await source.fetch_movie_detail("2026-07-09|123")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_movie_detail_returns_none_for_malformed_identifier() -> None:
    """An identifier missing the date/code separator is rejected without a fetch."""
    source = CinemathequeSource()

    with patch(
        "marquise.infrastructure.sources.cinematheque.gateways.source._fetch"
    ) as mock_fetch:
        result = await source.fetch_movie_detail("not-a-valid-identifier")

    assert result is None
    mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_movie_detail_returns_none_on_http_error() -> None:
    """An HTTP error while re-fetching the date page is treated as no data."""
    source = CinemathequeSource()

    with patch(
        "marquise.infrastructure.sources.cinematheque.gateways.source._fetch",
        side_effect=HTTPError("url", 404, "Not Found", {}, None),  # type: ignore[arg-type]
    ):
        result = await source.fetch_movie_detail("2026-07-09|123")

    assert result is None
