"""Showtime source for Cinéma Moderne.

Fetches from the ``/horaire/<year>/<month>`` schedule pages at
``https://www.cinemamoderne.com/``. Unlike Cinema Public or Cinémathèque
québécoise, the full month calendar (including showtimes, per-performance
ticket links, and film links) is server-rendered directly into the page's
HTML — there is no JSON-LD block and no AJAX endpoint.

Each month page renders a full calendar grid, so adjacent months overlap on
their boundary days (e.g. the July page also renders the trailing days of
June). Results are deduplicated by ``(movie_url, showtime)`` once all
months in the requested range have been fetched.

Film detail pages (``/films/details/<slug>/``) expose a structured
``<dl class="cm-List cm-List--columns">`` with director, country, year,
duration, etc., plus a synopsis paragraph and poster image, used for
``fetch_movie_detail``.
"""

from __future__ import annotations

import html as html_mod
import re
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

import certifi

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

BASE_URL = "https://www.cinemamoderne.com"

_DAY_START_RE = re.compile(
    r'<div\s+class="cm-Cal__day[^"]*"\s+data-day="(\d{4}-\d{2}-\d{2})"'
)
_EVENT_SPLIT_RE = re.compile(r'<div class="cm-Cal__day__event">')
_EVENT_TITLE_RE = re.compile(
    r'<div class="cm-Cal__day__event__title">\s*'
    r'<a href="([^"]+)"[^>]*>\s*'
    r'<span class="cm-Fat">([^<]+)</span>\s*<br>\s*(.*?)</a>',
    re.DOTALL,
)
_TICKET_URL_RE = re.compile(r'cm-CTA--red"[^>]*\bhref="([^"]+)"')
_EVENEMENT_ID_RE = re.compile(r"EvenementID=(\d+)")
_LANGUAGE_MARKER_RE = re.compile(r"\(([A-Za-z]{2,8})\)\s*$")

_DL_PAIR_RE = re.compile(r"<dt>([^<]+)</dt><dd>([^<]*)</dd>")
_ENTRY_CONTENT_RE = re.compile(
    r'<div class="cm-Entry__content[^"]*">.*?<p>(.*?)</p>', re.DOTALL
)
_POSTER_RE = re.compile(r'<div class="cm-Entry__image">\s*<img[^>]+data-src="([^"]+)"')
_DURATION_RE = re.compile(r"(\d+)")


def _fetch(url: str) -> str:
    """Fetch a URL with SSL verification and a spoofed User-Agent.

    Args:
        url: The URL to fetch.

    Returns:
        The response body as a string.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Marquise/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=_SSL_CONTEXT) as resp:
        return resp.read().decode()


def _schedule_url(year: int, month: int) -> str:
    """Build the schedule page URL for a given month.

    Args:
        year: The calendar year.
        month: The calendar month (1-12).

    Returns:
        The full URL of the ``/horaire/<year>/<month>`` page.
    """
    return f"{BASE_URL}/horaire/{year}/{month:02d}"


def _months_in_range(start: datetime, end: datetime) -> list[tuple[int, int]]:
    """List every ``(year, month)`` pair between two dates, inclusive.

    Args:
        start: The start of the date range.
        end: The end of the date range.

    Returns:
        A list of ``(year, month)`` tuples in chronological order.
    """
    months: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def _split_title_and_language(title: str) -> tuple[str, str | None]:
    """Strip a trailing parenthetical version marker off a title.

    Args:
        title: The film title, e.g. ``"Romería (VOSTF)"``.

    Returns:
        A ``(clean_title, marker)`` tuple, e.g. ``("Romería", "VOSTF")``.
        ``marker`` is ``None`` if the title has no such marker.
    """
    match = _LANGUAGE_MARKER_RE.search(title)
    if not match:
        return title, None
    return title[: match.start()].rstrip(), match.group(1)


def _clean_text(raw: str) -> str:
    """Strip HTML tags and normalize whitespace/entities in inline text.

    Args:
        raw: Raw HTML fragment.

    Returns:
        Unescaped, whitespace-collapsed plain text.
    """
    without_tags = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(html_mod.unescape(without_tags).split())


def _parse_day_events(day_html: str, date_str: str) -> list[dict[str, Any]]:
    """Parse showtime events from one day's HTML chunk.

    Args:
        day_html: The HTML between one ``cm-Cal__day`` div and the next.
        date_str: The day's date (``YYYY-MM-DD``), from ``data-day``.

    Returns:
        A list of plain dicts with keys ``movie_title``, ``showtime``,
        ``identifier``, ``external_id``, ``ticket_url``, ``room``,
        ``language``.
    """
    rows: list[dict[str, Any]] = []
    for event_chunk in _EVENT_SPLIT_RE.split(day_html)[1:]:
        title_match = _EVENT_TITLE_RE.search(event_chunk)
        if not title_match:
            continue
        movie_url, time_str, raw_title = title_match.groups()
        title, language = _split_title_and_language(_clean_text(raw_title))
        if not title:
            continue

        try:
            time_norm = datetime.strptime(time_str.strip(), "%H:%M").strftime("%H:%M")
        except ValueError:
            continue
        showtime = f"{date_str}T{time_norm}"

        ticket_match = _TICKET_URL_RE.search(event_chunk)
        ticket_url = ticket_match.group(1) if ticket_match else None

        external_id: str | None = None
        if ticket_url:
            evenement_match = _EVENEMENT_ID_RE.search(ticket_url)
            if evenement_match:
                external_id = f"{evenement_match.group(1)}-{showtime}"

        rows.append(
            {
                "movie_title": title,
                "showtime": showtime,
                "identifier": movie_url,
                "external_id": external_id,
                "ticket_url": ticket_url,
                "room": None,
                "language": language,
            }
        )
    return rows


def _parse_schedule_page(html: str) -> list[dict[str, Any]]:
    """Parse all showtime events from a month schedule page.

    Args:
        html: The full page HTML.

    Returns:
        A list of plain showtime dicts (see ``_parse_day_events``).
    """
    matches = list(_DAY_START_RE.finditer(html))
    rows: list[dict[str, Any]] = []
    for i, match in enumerate(matches):
        date_str = match.group(1)
        chunk_end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        day_html = html[match.end() : chunk_end]
        rows.extend(_parse_day_events(day_html, date_str))
    return rows


def _get_date_range(
    start_date: datetime | None, end_date: datetime | None
) -> tuple[datetime, datetime]:
    """Return a default date range when none is given.

    When both are None, defaults to today through 90 days from now.

    Args:
        start_date: Earliest showtime to include, or ``None``.
        end_date: Latest showtime to include, or ``None``.

    Returns:
        ``(start, end)`` tuple.
    """
    now = datetime.now()
    start = (
        start_date
        if start_date is not None
        else now.replace(hour=0, minute=0, second=0, microsecond=0)
    )
    end = end_date if end_date is not None else start + timedelta(days=90)
    return start, end


def fetch_showtimes(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Fetch showtimes for Cinéma Moderne.

    Fetches every ``/horaire/<year>/<month>`` page covering the requested
    date range concurrently, then deduplicates rows that appear on more
    than one month's page (each month renders a full calendar grid that
    overlaps its neighbours at the boundary).

    Args:
        start_date: Earliest showtime to include (inclusive).
        end_date: Latest showtime to include (inclusive).

    Returns:
        A list of plain dicts with keys ``movie_title``, ``showtime``,
        ``identifier``, ``external_id``, ``ticket_url``, ``room``,
        ``language``.
    """
    range_start, range_end = _get_date_range(start_date, end_date)
    months = _months_in_range(range_start, range_end)

    with ThreadPoolExecutor(max_workers=min(len(months), 10)) as executor:

        def _fetch_one(ym: tuple[int, int]) -> list[dict[str, Any]]:
            html = _fetch(_schedule_url(*ym))
            return _parse_schedule_page(html)

        futures = [executor.submit(_fetch_one, ym) for ym in months]
        deduped: dict[tuple[str, str], dict[str, Any]] = {}
        for future in futures:
            try:
                rows = future.result()
            except urllib.error.HTTPError:
                continue
            for row in rows:
                key = (row["identifier"], row["showtime"])
                deduped[key] = row

    range_start_date = range_start.date()
    range_end_date = range_end.date()
    results = [
        row
        for row in deduped.values()
        if range_start_date
        <= datetime.fromisoformat(row["showtime"]).date()
        <= range_end_date
    ]
    results.sort(key=lambda row: row["showtime"])
    return results


def _extract_cinemamoderne_film_detail(html: str) -> dict[str, Any]:
    """Extract enriched movie metadata from a Cinéma Moderne film page.

    Args:
        html: The HTML of the film detail page.

    Returns:
        A flat dict of movie metadata.
    """
    result: dict[str, Any] = {}

    pairs = dict(_DL_PAIR_RE.findall(html))

    directors_raw = pairs.get("Réalisation")
    if directors_raw and directors_raw.strip():
        directors = [d.strip() for d in directors_raw.split(",") if d.strip()]
        if directors:
            result["directors"] = directors

    countries_raw = pairs.get("Pays/Région")
    if countries_raw and countries_raw.strip():
        countries = [c.strip() for c in re.split(r"[,/]", countries_raw) if c.strip()]
        if countries:
            result["origin_countries"] = countries

    year_raw = pairs.get("Année")
    if year_raw and year_raw.strip().isdigit():
        result["release_year"] = int(year_raw.strip())

    duration_raw = pairs.get("Durée")
    if duration_raw:
        duration_match = _DURATION_RE.search(duration_raw)
        if duration_match:
            result["duration_minutes"] = int(duration_match.group(1))

    content_match = _ENTRY_CONTENT_RE.search(html)
    if content_match:
        description = _clean_text(content_match.group(1))
        if description:
            result["description"] = description

    poster_match = _POSTER_RE.search(html)
    if poster_match:
        result["poster_url"] = poster_match.group(1)

    return result


class CinemaModerneSource:
    """Showtime source for Cinéma Moderne (single venue)."""

    async def fetch_showtimes(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for Cinéma Moderne.

        Args:
            start_date: Earliest showtime to include (inclusive).
            end_date: Latest showtime to include (inclusive).

        Returns:
            A list of plain dicts with keys ``movie_title``, ``showtime``,
            ``identifier``, ``external_id``, ``ticket_url``, ``room``,
            ``language``.
        """
        return fetch_showtimes(start_date=start_date, end_date=end_date)

    async def fetch_movie_detail(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        """Fetch enriched movie metadata from a Cinéma Moderne film page.

        Args:
            identifier: The film detail page URL, as returned in a showtime
                row's ``identifier`` field (e.g.
                ``"https://www.cinemamoderne.com/films/details/kairos/"``).

        Returns:
            A dict of movie metadata, or ``None`` if the page cannot be
            fetched.
        """
        try:
            html = _fetch(identifier)
        except urllib.error.HTTPError:
            return None
        result = _extract_cinemamoderne_film_detail(html)
        return result or None
