"""Tests for the Cinéma Moderne showtime source gateway."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from marquise.infrastructure.sources.cinemamoderne.gateways.source import (
    CinemaModerneSource,
    _extract_cinemamoderne_film_detail,
    _parse_schedule_page,
    _split_title_and_language,
    fetch_showtimes,
)

_FILM_URL = "https://www.cinemamoderne.com/films/details/un-ete-en-hiver/"


def _event_html(
    *,
    movie_url: str = _FILM_URL,
    time_str: str = "15:00",
    title: str = "Un été en hiver",
    marker: str = " (VOSTF)",
    evenement_id: str = "21129",
) -> str:
    """Build one ``cm-Cal__day__event`` HTML block, mirroring the real markup."""
    ticket_url = (
        "https://cinemamoderne.ticketacces.net/fr/organisation/representations/"
        f"index.cfm?EvenementID={evenement_id}"
    )
    return (
        '<div class="cm-Cal__day__event">'
        '<div class="cm-Cal__day__event__title">'
        f'<a href="{movie_url}" data-gtm>'
        f'<span class="cm-Fat">{time_str}</span>'
        f"<br>{title}{marker}</a>"
        "</div>"
        '<div class="cm-Cal__day__event__card">'
        f'<a class="cm-CTA cm-CTA--red" target="_blank" href="{ticket_url}" '
        'title="Billetterie">Billetterie</a>'
        "</div>"
        "</div>"
    )


def _day_html(date_str: str, events_html: str = "", *, disabled: bool = False) -> str:
    """Build one ``cm-Cal__day`` HTML block."""
    disabled_class = " cm-Cal__day--disabled " if disabled else " "
    return (
        f'<div class="cm-Cal__day{disabled_class}" data-day="{date_str}">'
        '<div class="cm-Cal__day__head"><div class="cm-Title">1</div></div>'
        f'<div class="cm-Cal__day__body">{events_html}</div>'
        "</div>"
    )


def _schedule_page_html(*day_blocks: str) -> str:
    """Wrap day blocks in a minimal page shell around a ``cm-Cal`` container."""
    return f'<html><body><div class="cm-Cal">{"".join(day_blocks)}</div></body></html>'


def _film_detail_html(
    *,
    director: str = "Shō Miyake",
    country: str = "Japon",
    year: str = "2025",
    duration: str = "89 minutes",
    description: str = "Un été, Nagisa rencontre Natsuo au bord de la mer.",
    poster_url: str = (
        "https://www.cinemamoderne.com/wp-content/uploads/2026/06/poster.jpg"
    ),
) -> str:
    """Build a minimal film detail page around the real markup shape."""
    return (
        "<html><body>"
        '<div class="cm-Entry__lists" style="max-width:235px">'
        "<dl class='cm-List cm-List--columns'>"
        f"<dt>Réalisation</dt><dd>{director}</dd>"
        f"<dt>Pays/Région</dt><dd>{country}</dd>"
        f"<dt>Année</dt><dd>{year}</dd>"
        f"<dt>Durée</dt><dd>{duration}</dd>"
        "</dl></div>"
        f'<div class="cm-Entry__image"><img data-src="{poster_url}"></div>'
        '<div class="cm-Entry__content user-edit"><div class="user-edit">'
        f"<p>{description}</p>"
        "</div></div>"
        "</body></html>"
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Romería (VOSTF)", ("Romería", "VOSTF")),
        ("Erupcja (VOSTA)", ("Erupcja", "VOSTA")),
        (
            "Un été en hiver (Two Seasons, Two Strangers) (VOSTF)",
            (
                "Un été en hiver (Two Seasons, Two Strangers)",
                "VOSTF",
            ),
        ),
        ("A Movie With No Marker", ("A Movie With No Marker", None)),
    ],
)
def test_split_title_and_language_strips_trailing_marker(
    title: str, expected: tuple[str, str | None]
) -> None:
    """A trailing parenthetical version marker is stripped off the title."""
    assert _split_title_and_language(title) == expected


def test_parse_schedule_page_builds_showtime_rows() -> None:
    """A day block with one event yields one showtime row."""
    html = _schedule_page_html(_day_html("2026-07-13", _event_html()))

    rows = _parse_schedule_page(html)

    assert rows == [
        {
            "movie_title": "Un été en hiver",
            "showtime": "2026-07-13T15:00",
            "identifier": _FILM_URL,
            "external_id": "21129-2026-07-13T15:00",
            "ticket_url": (
                "https://cinemamoderne.ticketacces.net/fr/organisation/"
                "representations/index.cfm?EvenementID=21129"
            ),
            "room": None,
            "language": "VOSTF",
        }
    ]


def test_parse_schedule_page_normalizes_single_digit_hour() -> None:
    """A single-digit hour like '9:30' is zero-padded to '09:30'."""
    html = _schedule_page_html(_day_html("2026-07-13", _event_html(time_str="9:30")))

    rows = _parse_schedule_page(html)

    assert rows[0]["showtime"] == "2026-07-13T09:30"


def test_parse_schedule_page_handles_multiple_events_same_day() -> None:
    """Multiple events on the same day each become their own row."""
    events = _event_html(time_str="15:00", evenement_id="1") + _event_html(
        time_str="17:00",
        evenement_id="2",
        movie_url=("https://www.cinemamoderne.com/films/details/other-film/"),
    )
    html = _schedule_page_html(_day_html("2026-07-13", events))

    rows = _parse_schedule_page(html)

    assert [row["showtime"] for row in rows] == [
        "2026-07-13T15:00",
        "2026-07-13T17:00",
    ]


def test_parse_schedule_page_includes_disabled_days() -> None:
    """Days marked '--disabled' (past days, per the live site) still parse."""
    html = _schedule_page_html(_day_html("2026-07-01", _event_html(), disabled=True))

    rows = _parse_schedule_page(html)

    assert len(rows) == 1


def test_parse_schedule_page_skips_days_without_events() -> None:
    """A day block with no events yields no rows."""
    html = _schedule_page_html(_day_html("2026-07-13"))

    assert _parse_schedule_page(html) == []


@pytest.mark.asyncio
async def test_fetch_showtimes_fetches_each_month_in_range() -> None:
    """One page is fetched per (year, month) covering [start_date, end_date]."""
    calls: list[str] = []

    def fake_fetch(url: str) -> str:
        calls.append(url)
        return _schedule_page_html()

    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        side_effect=fake_fetch,
    ):
        fetch_showtimes(
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 9, 1),
        )

    assert sorted(calls) == [
        "https://www.cinemamoderne.com/horaire/2026/07",
        "https://www.cinemamoderne.com/horaire/2026/08",
        "https://www.cinemamoderne.com/horaire/2026/09",
    ]


@pytest.mark.asyncio
async def test_fetch_showtimes_dedupes_rows_from_overlapping_months() -> None:
    """The same (movie, showtime) appearing on two month pages is kept once.

    Each month page renders a full calendar grid, so boundary days (e.g. the
    trailing days of June rendered on the July page) can appear on two
    consecutive month pages with identical content.
    """
    shared_day = _day_html("2026-07-31", _event_html())

    def fake_fetch(url: str) -> str:
        if url.endswith("2026/07"):
            return _schedule_page_html(shared_day)
        return _schedule_page_html(shared_day)

    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        side_effect=fake_fetch,
    ):
        rows = fetch_showtimes(
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 8, 31),
        )

    assert len(rows) == 1


@pytest.mark.asyncio
async def test_fetch_showtimes_excludes_out_of_range_dates() -> None:
    """Rows outside the requested [start, end] window are filtered out."""
    html = _schedule_page_html(
        _day_html("2026-06-29", _event_html(time_str="15:00")),
        _day_html("2026-07-13", _event_html(time_str="17:00")),
    )

    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        return_value=html,
    ):
        rows = fetch_showtimes(
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 7, 31),
        )

    assert [row["showtime"] for row in rows] == ["2026-07-13T21:00:00+00:00"]


@pytest.mark.asyncio
async def test_fetch_showtimes_converts_montreal_local_to_utc() -> None:
    """Showtime rows carry a real UTC offset, DST-adjusted for the month."""
    html = _schedule_page_html(
        _day_html("2026-07-13", _event_html(time_str="17:00")),
    )

    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        return_value=html,
    ):
        rows = fetch_showtimes(
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 7, 31),
        )

    # July is EDT (UTC-4): 17:00 Montreal -> 21:00 UTC.
    assert rows[0]["showtime"] == "2026-07-13T21:00:00+00:00"


@pytest.mark.asyncio
async def test_fetch_showtimes_converts_montreal_local_to_utc_in_winter() -> None:
    """Winter showtimes convert using EST (UTC-5), not a fixed offset."""
    html = _schedule_page_html(
        _day_html("2026-01-13", _event_html(time_str="17:00")),
    )

    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        return_value=html,
    ):
        rows = fetch_showtimes(
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )

    assert rows[0]["showtime"] == "2026-01-13T22:00:00+00:00"


@pytest.mark.asyncio
async def test_fetch_showtimes_accepts_timezone_aware_range() -> None:
    """Timezone-aware start/end (as ImportScreeningsUseCase passes) don't crash."""
    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        return_value=_schedule_page_html(),
    ):
        rows = fetch_showtimes(
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC) + timedelta(days=7),
        )

    assert rows == []


@pytest.mark.asyncio
async def test_fetch_showtimes_skips_months_that_fail_to_fetch() -> None:
    """An HTTPError for one month's page doesn't abort the whole fetch."""

    def fake_fetch(url: str) -> str:
        if url.endswith("2026/07"):
            raise HTTPError(url, 500, "Server Error", {}, None)  # type: ignore[arg-type]
        return _schedule_page_html(_day_html("2026-08-01", _event_html()))

    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        side_effect=fake_fetch,
    ):
        rows = fetch_showtimes(
            start_date=datetime(2026, 7, 1),
            end_date=datetime(2026, 8, 31),
        )

    assert len(rows) == 1


@pytest.mark.asyncio
async def test_source_fetch_showtimes_delegates_to_module_function() -> None:
    """CinemaModerneSource.fetch_showtimes wraps the module-level function."""
    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        return_value=_schedule_page_html(),
    ):
        source = CinemaModerneSource()
        rows = await source.fetch_showtimes(
            start_date=datetime.now(), end_date=datetime.now()
        )

    assert rows == []


def test_extract_film_detail_parses_all_fields() -> None:
    """A well-formed film detail page yields all enrichment fields."""
    html = _film_detail_html()

    result = _extract_cinemamoderne_film_detail(html)

    assert result == {
        "directors": ["Shō Miyake"],
        "origin_countries": ["Japon"],
        "release_year": 2025,
        "duration_minutes": 89,
        "description": "Un été, Nagisa rencontre Natsuo au bord de la mer.",
        "poster_url": (
            "https://www.cinemamoderne.com/wp-content/uploads/2026/06/poster.jpg"
        ),
    }


def test_extract_film_detail_splits_multiple_directors() -> None:
    """A comma-separated director field becomes a list of names."""
    html = _film_detail_html(director="Jane Doe, John Smith")

    result = _extract_cinemamoderne_film_detail(html)

    assert result["directors"] == ["Jane Doe", "John Smith"]


def test_extract_film_detail_handles_missing_fields() -> None:
    """A page with no matching markup yields an empty dict."""
    html = "<html><body>No film details here</body></html>"

    assert _extract_cinemamoderne_film_detail(html) == {}


@pytest.mark.asyncio
async def test_fetch_movie_detail_returns_enrichment_from_identifier_url() -> None:
    """fetch_movie_detail fetches the identifier URL and extracts metadata."""
    html = _film_detail_html()

    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        return_value=html,
    ) as mock_fetch:
        source = CinemaModerneSource()
        result = await source.fetch_movie_detail(_FILM_URL)

    mock_fetch.assert_called_once_with(_FILM_URL)
    assert result is not None
    assert result["directors"] == ["Shō Miyake"]


@pytest.mark.asyncio
async def test_fetch_movie_detail_returns_none_on_http_error() -> None:
    """An HTTP error while fetching the film page is treated as no data."""
    with patch(
        "marquise.infrastructure.sources.cinemamoderne.gateways.source._fetch",
        side_effect=HTTPError(_FILM_URL, 404, "Not Found", {}, None),  # type: ignore[arg-type]
    ):
        source = CinemaModerneSource()
        result = await source.fetch_movie_detail(_FILM_URL)

    assert result is None
