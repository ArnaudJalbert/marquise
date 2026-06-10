"""Showtime source for Cinema Public.

Fetches from https://cinemapublic.ca/en/schedule/
and the AJAX ``load_more_weeks`` endpoint to get all future showtimes.

The initial page provides JSON-LD structured data (with prices) for ~2 weeks.
Additional weeks are fetched via AJAX and parsed from HTML.
"""

from __future__ import annotations

import html as html_mod
import json
import re
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

SCHEDULE_URL = "https://cinemapublic.ca/en/schedule/"
AJAX_URL = "https://cinemapublic.ca/wp-admin/admin-ajax.php"

VENUE_MAP: dict[str, str] = {
    "casa-d-italia": "Cinema Public — Casa d'Italia",
    "livart": "Cinema Public — Livart",
}

_VENUE_FRAGMENTS: dict[str, str] = {
    "casa-d-italia": "#casa-d-italia",
    "livart": "#livart-chaises-pliantes",
}

_WEEKS_PER_OFFSET = 2


def _fetch(url: str, data: bytes | None = None) -> str:
    """Fetch a URL with SSL verification disabled.

    Args:
        url: The URL to fetch.
        data: Optional POST body bytes.

    Returns:
        The response body as a string.
    """
    ctx = ssl._create_unverified_context()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Marquise/1.0)"}
    if data is not None:
        headers["Referer"] = SCHEDULE_URL
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        return resp.read().decode()


def _fetch_ajax_page(offset: int) -> str:
    """Fetch one page of the ``load_more_weeks`` AJAX endpoint.

    Args:
        offset: Number of weeks to skip (0 = current, 2 = +2 weeks, etc.).

    Returns:
        The HTML fragment returned by the endpoint.
    """
    body = f"action=load_more_weeks&offset={offset}&lang=en".encode()
    return _fetch(AJAX_URL, data=body)


def _parse_ajax_html(html: str, venue: str) -> list[dict[str, Any]]:
    """Parse showtime events from an AJAX HTML fragment.

    Args:
        html: The HTML returned by ``load_more_weeks``.
        venue: Target venue slug.

    Returns:
        A list of plain dicts with keys ``movie_title``, ``showtime``,
        ``movie_url``, ``ticket_url``.
    """
    results: list[dict[str, Any]] = []

    # Split into day blocks
    day_blocks = re.split(r'<div\s+class="cm-Cal__day"', html)
    for block in day_blocks:
        # Extract date
        date_match = re.search(r'data-day="([^"]+)"', block)
        if not date_match:
            continue
        date_str = date_match.group(1)

        # Find the first closing of the day__body
        # Split into event blocks within this day
        event_blocks = re.split(r'<div\s+class="cm-Cal__day__event"', block)
        for ev_block in event_blocks[1:]:  # skip the first (header) part
            # Check venue
            addr_match = re.search(r'data-address="([^"]*)"', ev_block)
            if not addr_match or addr_match.group(1) != venue:
                continue

            # Time
            time_match = re.search(r'<span\s+class="mb-2">([^<]+)</span>', ev_block)
            if not time_match:
                continue
            # Convert 12-hour time (e.g. "2:00 PM") to 24-hour ISO format
            time_str = time_match.group(1).strip()
            try:
                time_norm = datetime.strptime(time_str, "%I:%M %p").strftime("%H:%M")
            except ValueError:
                time_norm = time_str

            showtime = f"{date_str}T{time_norm}"

            # Movie link
            link_match = re.search(
                r'<a\s+href="([^"]*)"[^>]*>.*?<span>([^<]+)</span>',
                ev_block,
                re.DOTALL,
            )
            if not link_match:
                continue
            movie_url = link_match.group(1)
            if movie_url and not movie_url.startswith("http"):
                movie_url = f"https://cinemapublic.ca{movie_url}"
            movie_title = html_mod.unescape(link_match.group(2).strip())

            # Subtitle language
            lang_match = re.search(r"<span>\(([^)]+)\)</span>", ev_block)
            subtitle_language: str | None = lang_match.group(1) if lang_match else None

            # Ticket link
            ticket_match = re.search(
                r'<a\s+[^>]*class="btn[^"]*"[^>]*href="([^"]*)"[^>]*>'
                r"Tickets?\s*</a>",
                ev_block,
                re.DOTALL,
            )
            ticket_url: str = ticket_match.group(1) if ticket_match else ""

            # With-mention
            with_match = re.search(r"With\s+([^<]+?)(?:\s*</|$)", ev_block)
            special_notes: list[str] = []
            if with_match:
                notes_text = html_mod.unescape(with_match.group(1).strip())
                special_notes.append(f"With {notes_text}")

            results.append(
                {
                    "movie_title": movie_title,
                    "showtime": showtime,
                    "subtitle_language": subtitle_language,
                    "special_notes": special_notes or None,
                    "movie_url": movie_url,
                    "ticket_url": ticket_url,
                }
            )

    return results


def _extract_jsonld(html: str) -> dict[str, Any] | None:
    """Extract the schedule JSON-LD block from the page HTML.

    Args:
        html: The full page HTML.

    Returns:
        The parsed JSON-LD dict, or None if not found.
    """
    matches = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    for match in matches:
        data = json.loads(match)
        if isinstance(data, dict):
            graph = data.get("@graph", data)
            if isinstance(graph, dict) and "itemListElement" in graph:
                return graph
    return None


def _parse_jsonld_showtimes(
    graph: dict[str, Any], venue: str
) -> dict[str, list[dict[str, Any]]]:
    """Parse showtimes from the JSON-LD graph, grouped by ``YYYY-MM-DD``.

    Args:
        graph: The ``@graph`` dict from JSON-LD.
        venue: Target venue slug.

    Returns:
        A dict mapping ``YYYY-MM-DD`` to a list of showtime dicts.
    """
    items = graph.get("itemListElement", [])
    by_date: dict[str, list[dict[str, Any]]] = {}

    for entry in items:
        event = entry.get("item", {})
        if not event:
            continue

        location = event.get("location", {})
        location_id = location.get("@id") if isinstance(location, dict) else None
        if not location_id or not location_id.endswith(_VENUE_FRAGMENTS.get(venue, "")):
            continue

        start_date_str: str = event.get("startDate", "")
        if not start_date_str:
            continue
        try:
            dt = datetime.fromisoformat(start_date_str)
        except ValueError:
            continue

        date_key = dt.strftime("%Y-%m-%d")
        showtime = dt.strftime("%Y-%m-%dT%H:%M")

        work_presented = event.get("workPresented", {}) or {}
        movie_title: str = html_mod.unescape(
            work_presented.get("name", event.get("name", "Untitled"))
        )
        movie_url: str = work_presented.get("url", "")

        ticket_url: str = event.get("offers", {}).get("url", "")
        if ticket_url.startswith("https:///"):
            ticket_url = ticket_url.replace("https:///", "https://")

        by_date.setdefault(date_key, []).append(
            {
                "movie_title": movie_title,
                "showtime": showtime,
                "subtitle_language": None,
                "special_notes": None,
                "movie_url": movie_url,
                "ticket_url": ticket_url,
            }
        )

    return by_date


def _get_date_range(
    start_date: datetime | None, end_date: datetime | None
) -> tuple[datetime, datetime]:
    """Return a default date range when none is given.

    When both are None, defaults to today through 90 days from now.

    Returns:
        ``(start, end)`` tuple.
    """
    now = datetime.now()
    if start_date is None:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = start_date
    if end_date is None:
        end = start + timedelta(days=90)
    else:
        end = end_date
    return start, end


def _needed_offsets(
    first_initial_date: str | None,
    range_end: datetime,
) -> list[int]:
    """Determine which AJAX offsets are needed to cover *range_end*.

    Initial page covers the same period as offset 0 (~14 days starting at
    *first_initial_date*).  Each additional offset adds 14 days.

    Args:
        first_initial_date: The first date covered by the initial page
            (``YYYY-MM-DD``), or None if none.
        range_end: The end of the requested date range.

    Returns:
        A list of offset integers (e.g. ``[2, 4, 6]``) to fetch, or an
        empty list if no AJAX calls are needed.
    """
    if not first_initial_date:
        return []

    initial_start = datetime.strptime(first_initial_date, "%Y-%m-%d")
    days_after_initial = (range_end - initial_start).days

    if days_after_initial <= 14:
        return []

    # offset=n covers days n*7 to n*7+13
    # We need the smallest even offset n where n*7+13 >= days_after_initial
    max_offset = 2 * ((days_after_initial + 13) // 14)
    return list(range(2, max_offset + 1, 2))


def fetch_showtimes(
    cinema_name: str = "casa-d-italia",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Fetch showtimes for a Cinema Public venue.

    Fetches the initial page (JSON-LD) and calls the AJAX
    ``load_more_weeks`` endpoint to cover the requested date range.

    Args:
        cinema_name: One of ``"casa-d-italia"`` or ``"livart"``.
        start_date: Earliest showtime to include (inclusive).
        end_date: Latest showtime to include (inclusive).

    Returns:
        A list of plain dicts with keys ``movie_title``, ``showtime``,
        ``movie_url``, ``ticket_url``, ``special_notes``,
        ``subtitle_language``.

    Raises:
        ValueError: If ``cinema_name`` is not a recognised venue.
    """
    if cinema_name not in VENUE_MAP:
        raise ValueError(
            f"cinema_name must be one of {set(VENUE_MAP.keys())}, got '{cinema_name}'"
        )

    range_start, range_end = _get_date_range(start_date, end_date)

    # ------------------------------------------------------------------
    # 1.  Fetch the initial page to get the first ~2 weeks with prices.
    # ------------------------------------------------------------------
    page_html = _fetch(SCHEDULE_URL)
    graph = _extract_jsonld(page_html)
    jsonld_by_date: dict[str, list[dict[str, Any]]] = (
        _parse_jsonld_showtimes(graph, cinema_name) if graph else {}
    )

    ld_dates = sorted(jsonld_by_date.keys())

    # ------------------------------------------------------------------
    # 2.  Determine which AJAX offsets are needed and fetch them.
    # ------------------------------------------------------------------
    first_ld = ld_dates[0] if ld_dates else None
    offsets = _needed_offsets(first_ld, range_end)

    ajax_results_by_date: dict[str, list[dict[str, Any]]] = {}

    if offsets:
        with ThreadPoolExecutor(max_workers=min(len(offsets), 10)) as executor:

            def _fetch_one(o: int) -> list[dict[str, Any]]:
                html = _fetch_ajax_page(o)
                return _parse_ajax_html(html, cinema_name)

            futures = [executor.submit(_fetch_one, o) for o in offsets]
            for future in futures:
                try:
                    events = future.result()
                except urllib.error.HTTPError:
                    continue
                for ev in events:
                    if ev["ticket_url"].startswith("https:///"):
                        ev["ticket_url"] = ev["ticket_url"].replace(
                            "https:///", "https://"
                        )
                    date_key = ev["showtime"][:10]
                    ajax_results_by_date.setdefault(date_key, []).append(ev)

    # ------------------------------------------------------------------
    # 3.  Merge JSON-LD data and AJAX data (JSON-LD wins on overlap).
    # ------------------------------------------------------------------
    all_dates = sorted(set(jsonld_by_date.keys()) | set(ajax_results_by_date.keys()))
    all_by_date: dict[str, list[dict[str, Any]]] = {}
    for date_key in all_dates:
        if date_key in jsonld_by_date:
            all_by_date[date_key] = jsonld_by_date[date_key]
        elif date_key in ajax_results_by_date:
            all_by_date[date_key] = ajax_results_by_date[date_key]

    # ------------------------------------------------------------------
    # 4.  Flatten, sort, and filter by date range.
    # ------------------------------------------------------------------
    results: list[dict[str, Any]] = []
    for date_key in all_dates:
        dt = datetime.strptime(date_key, "%Y-%m-%d")
        if dt < range_start or dt > range_end:
            continue
        events = sorted(
            all_by_date[date_key],
            key=lambda e: e["showtime"],
        )
        for ev in events:
            try:
                ev_dt = datetime.fromisoformat(ev["showtime"])
            except ValueError:
                ev_dt = datetime.strptime(ev["showtime"], "%Y-%m-%dT%I:%M %p")
            if ev_dt < range_start or ev_dt > range_end:
                continue
            results.append(ev)

    return results


class CinemaPublicSource:
    """Showtime source for Cinema Public (Casa d'Italia and Livart venues)."""

    async def fetch_showtimes(
        self,
        cinema_name: str = "casa-d-italia",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for a Cinema Public venue.

        Args:
            cinema_name: One of ``"casa-d-italia"`` or ``"livart"``.
            start_date: Earliest showtime to include (inclusive).
            end_date: Latest showtime to include (inclusive).

        Returns:
            A list of plain dicts with keys ``movie_title``, ``showtime``,
            ``movie_url``, ``ticket_url``.

        Raises:
            ValueError: If ``cinema_name`` is not a recognised venue.
        """
        return fetch_showtimes(
            cinema_name=cinema_name,
            start_date=start_date,
            end_date=end_date,
        )
