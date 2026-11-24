"""Tests for the Théâtre Outremont showtime source gateway.

The gateway reads the Tuxedo Billet Firebase RTDB backend. These tests patch
the bootstrap and read helpers so no network is used, feeding them the RTDB
document shapes captured from the live backend.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from marquise.infrastructure.sources.outremont import (
    OutremontSource,
    _clean_title,
    _extract_outremont_film_detail,
    _show_rows,
    fetch_showtimes,
)

_MODULE = "marquise.infrastructure.sources.outremont"

# firstgroup report-category id -> name, mirroring the real node.
_CATEGORY_NAMES = {
    "cat-cinema": "Cinéma",
    "cat-musique": "Musique",
}

# 2026-07-20T20:00:00Z and 2026-07-20T23:30:00Z in epoch millis.
_MS_1600 = 1784577600000
_MS_1930 = 1784590200000

_BLUE_VELVET_DESC = (
    "<p><strong>Blue Velvet</strong></p>"
    "<p><br></p>"
    "<p><span>Version originale avec sous-titres français. États-Unis. 1986. "
    "Drame / Thriller. 120 min. (13 ans et +)</span></p>"
    "<p><span>Avec Kyle MacLachlan, Isabella Rossellini, Dennis Hopper</span></p>"
    "<p><br></p>"
    "<p><span>Dans une petite ville américaine, Jeffrey trouve une oreille.</span></p>"
)

_GATEAU_DESC = (
    "<p><strong>Le Gâteau du président (Mamlaket Al-Qasab)</strong></p>"
    "<p><br></p>"
    "<p><span>Iraq, Qatar, Etats-Unis. 2025. Drame. 106 min. VOSTFr (G)</span></p>"
    "<p><span>Avec Banin Ahmad Nayef, Sajad Mohamad Qasem</span></p>"
    "<p><span>En 1990, Lamia est choisie pour cuisiner un gâteau.</span></p>"
)


def _cinema_show(
    *,
    slug: str = "cine-outremont-blue-velvet",
    title: str = "Ciné-Outremont | Blue Velvet",
    events: dict[str, int] | None = None,
    description: str = _BLUE_VELVET_DESC,
    subtitle: str = "Un film de David Lynch",
    poster: str | None = "https://img/blue-velvet.png",
    category: str = "cat-cinema",
) -> dict[str, Any]:
    """Build a show document mirroring the real RTDB shape."""
    show: dict[str, Any] = {
        "uniqueShowId": slug,
        "title": title,
        "events": events if events is not None else {"ev-1": _MS_1930},
        "reportCategories": {"firstgroup": category},
        "description": description,
        "subTitles": [{"title": subtitle}],
    }
    if poster is not None:
        show["images"] = {"main": poster}
    return show


def test_clean_title_strips_cadre_prefix() -> None:
    """A leading ``"<cadre> | "`` prefix is removed from the title."""
    assert _clean_title("Ciné-Outremont | Blue Velvet") == "Blue Velvet"
    assert _clean_title("Producteur invité | Soirée") == "Soirée"


def test_clean_title_without_prefix_is_unchanged() -> None:
    """A title without a pipe prefix is returned unchanged."""
    assert _clean_title("Blue Velvet") == "Blue Velvet"


def test_show_rows_one_row_per_event_with_utc_instant() -> None:
    """Each event becomes a row with its exact UTC showtime and stable ids."""
    show = _cinema_show(events={"ev-a": _MS_1600, "ev-b": _MS_1930})
    rows = _show_rows(show, "show-key-1")

    assert len(rows) == 2
    by_event = {r["external_id"]: r for r in rows}
    assert by_event["ev-a"]["showtime"] == "2026-07-20T20:00:00+00:00"
    assert by_event["ev-b"]["showtime"] == "2026-07-20T23:30:00+00:00"
    row = by_event["ev-a"]
    assert row["movie_title"] == "Blue Velvet"
    assert row["identifier"] == "show-key-1"
    assert row["ticket_url"] == (
        "https://theatreoutremont.tuxedobillet.com/web/cine-outremont-blue-velvet"
    )
    assert row["room"] is None
    assert row["language"] is None


def test_show_rows_skips_non_numeric_event() -> None:
    """Non-numeric event values are ignored rather than raising."""
    show = _cinema_show(events={"ev-a": _MS_1600, "ev-bad": "soon"})  # type: ignore[dict-item]
    rows = _show_rows(show, "k")
    assert [r["external_id"] for r in rows] == ["ev-a"]


def test_fetch_showtimes_filters_by_category_and_range_sorted() -> None:
    """Cinema shows in range are returned, sorted; concerts/out-of-range dropped."""
    shows = {
        "k-cine": _cinema_show(events={"ev-a": _MS_1600, "ev-b": _MS_1930}),
        "k-concert": _cinema_show(
            slug="chambristes",
            title="Musique | Concert",
            category="cat-musique",
            events={"ev-c": _MS_1600},
        ),
        "k-old": _cinema_show(
            slug="cine-old",
            events={"ev-d": 1500000000000},  # 2017 — out of range
        ),
    }
    with (
        patch(f"{_MODULE}._bootstrap", return_value=("https://db", "tok", "chan")),
        patch(f"{_MODULE}._read_category_names", return_value=_CATEGORY_NAMES),
        patch(f"{_MODULE}._read_shows", return_value=shows),
    ):
        rows = fetch_showtimes(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 12, 31, tzinfo=UTC)
        )

    assert [r["showtime"] for r in rows] == [
        "2026-07-20T20:00:00+00:00",
        "2026-07-20T23:30:00+00:00",
    ]
    assert {r["movie_title"] for r in rows} == {"Blue Velvet"}


def test_fetch_showtimes_accepts_naive_dates() -> None:
    """Naive start/end datetimes are treated as UTC (no comparison error)."""
    shows = {"k-cine": _cinema_show(events={"ev-a": _MS_1600})}
    with (
        patch(f"{_MODULE}._bootstrap", return_value=("https://db", "tok", "chan")),
        patch(f"{_MODULE}._read_category_names", return_value=_CATEGORY_NAMES),
        patch(f"{_MODULE}._read_shows", return_value=shows),
    ):
        rows = fetch_showtimes(datetime(2026, 1, 1), datetime(2026, 12, 31))
    assert len(rows) == 1


def test_extract_detail_full_metadata_blue_velvet() -> None:
    """A standard description yields the full field set (language line stripped)."""
    detail = _extract_outremont_film_detail(_cinema_show())

    assert detail["poster_url"] == "https://img/blue-velvet.png"
    assert detail["directors"] == ["David Lynch"]
    assert detail["release_year"] == 1986
    assert detail["duration_minutes"] == 120
    assert detail["genres"] == ["Drame", "Thriller"]
    assert detail["origin_countries"] == ["États-Unis"]  # language sentence stripped
    assert detail["rating"] == "13 ans et +"
    assert detail["cast"] == [
        "Kyle MacLachlan",
        "Isabella Rossellini",
        "Dennis Hopper",
    ]
    assert detail["description"].startswith("Dans une petite ville")
    assert "original_title" not in detail


def test_extract_detail_original_title_and_multi_country() -> None:
    """A parenthetical title yields original_title; countries split on commas."""
    detail = _extract_outremont_film_detail(
        _cinema_show(
            slug="cine-outremont-ou-le-gateau-du-president",
            title="Ciné-Outremont | Le Gâteau du président",
            description=_GATEAU_DESC,
            subtitle="Un film d'Hasan Hadi",
        )
    )
    assert detail["original_title"] == "Mamlaket Al-Qasab"
    assert detail["origin_countries"] == ["Iraq", "Qatar", "Etats-Unis"]
    assert detail["release_year"] == 2025
    assert detail["directors"] == ["Hasan Hadi"]  # "Un film d'..." elision handled
    assert detail["rating"] == "G"


def test_extract_detail_missing_metadata_degrades_gracefully() -> None:
    """A show whose description lacks the standard line still yields partials."""
    detail = _extract_outremont_film_detail(
        _cinema_show(
            description="<p><span>Une rétrospective spéciale.</span></p>",
            subtitle="Un film de Alice Ronfard",
            poster=None,
        )
    )
    assert detail == {
        "directors": ["Alice Ronfard"],
        "description": "Une rétrospective spéciale.",
    }


@pytest.mark.asyncio
async def test_source_fetch_showtimes() -> None:
    """The async wrapper returns mapped cinema rows."""
    shows = {"k-cine": _cinema_show(events={"ev-a": _MS_1600})}
    with (
        patch(f"{_MODULE}._bootstrap", return_value=("https://db", "tok", "chan")),
        patch(f"{_MODULE}._read_category_names", return_value=_CATEGORY_NAMES),
        patch(f"{_MODULE}._read_shows", return_value=shows),
    ):
        rows = await OutremontSource().fetch_showtimes(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 12, 31, tzinfo=UTC)
        )
    assert len(rows) == 1
    assert rows[0]["movie_title"] == "Blue Velvet"


@pytest.mark.asyncio
async def test_source_fetch_movie_detail_reads_single_show() -> None:
    """fetch_movie_detail reads the one show by key and returns its metadata."""
    with (
        patch(f"{_MODULE}._bootstrap", return_value=("https://db", "tok", "chan")),
        patch(f"{_MODULE}._read_show", return_value=_cinema_show()) as read_show,
    ):
        detail = await OutremontSource().fetch_movie_detail("show-key-1")

    read_show.assert_called_once_with("https://db", "tok", "chan", "show-key-1")
    assert detail is not None
    assert detail["directors"] == ["David Lynch"]
    assert detail["release_year"] == 1986


@pytest.mark.asyncio
async def test_source_fetch_movie_detail_unknown_show() -> None:
    """An unknown key (no show doc) yields None."""
    with (
        patch(f"{_MODULE}._bootstrap", return_value=("https://db", "tok", "chan")),
        patch(f"{_MODULE}._read_show", return_value=None),
    ):
        detail = await OutremontSource().fetch_movie_detail("missing")
    assert detail is None


@pytest.mark.asyncio
async def test_source_fetch_movie_detail_http_error() -> None:
    """An HTTP error during bootstrap/read yields None."""
    with patch(
        f"{_MODULE}._bootstrap",
        side_effect=HTTPError("https://db", 500, "err", {}, None),  # type: ignore[arg-type]
    ):
        detail = await OutremontSource().fetch_movie_detail("show-key-1")
    assert detail is None
