"""Showtime source for Cine Starz server-rendered schedules and JSON-LD pages."""

from __future__ import annotations

import html
import json
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import certifi

from marquise.infrastructure.sources._timezone import montreal_local_to_utc_iso

BASE_URL = "https://cinestarz.ca"
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_ITEM_SPLIT_RE = re.compile(r'<div class="nowPlaying__item[^>]*>')
_MOVIE_LINK_RE = re.compile(
    r'<a class="nowPlaying__movieLink" href="([^"]+)">\s*(.*?)\s*</a>',
    re.DOTALL,
)
_PERFORMANCE_SPLIT_RE = re.compile(r'<div class="performance__item">')
_TIME_RE = re.compile(r"<span>\s*([0-9]{1,2}:[0-9]{2}\s*[AP]M)\s*</span>")
_TICKET_PATH_RE = re.compile(r"window\.location='(/movies/[^']+)'")
_JSON_LD_RE = re.compile(
    r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL
)


def _fetch(url: str) -> str:
    """Fetch URL with SSL verification and browser User-Agent."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; Marquise/1.0)"}
    )
    with urllib.request.urlopen(request, context=_SSL_CONTEXT) as response:
        return response.read().decode()


def _parse_schedule(html_body: str, date: datetime) -> list[dict[str, Any]]:
    """Parse enabled showtimes from one venue's schedule fragment."""
    rows: list[dict[str, Any]] = []
    date_str = date.strftime("%Y-%m-%d")
    for item in _ITEM_SPLIT_RE.split(html_body)[1:]:
        movie_match = _MOVIE_LINK_RE.search(item)
        if not movie_match:
            continue
        title = html.unescape(movie_match.group(2)).strip()
        if not title:
            continue
        for performance in _PERFORMANCE_SPLIT_RE.split(item)[1:]:
            time_match = _TIME_RE.search(performance)
            ticket_match = _TICKET_PATH_RE.search(performance)
            if not time_match or not ticket_match:
                continue
            try:
                time = datetime.strptime(time_match.group(1).upper(), "%I:%M %p")
            except ValueError:
                continue
            ticket_path = ticket_match.group(1)
            rows.append(
                {
                    "movie_title": title,
                    "showtime": montreal_local_to_utc_iso(
                        date_str, time.strftime("%H:%M")
                    ),
                    "identifier": urljoin(BASE_URL, movie_match.group(1)),
                    "external_id": ticket_path.removesuffix("/ticket-selection").rsplit(
                        "/", 1
                    )[-1],
                    "ticket_url": urljoin(BASE_URL, ticket_path),
                    "room": None,
                    "language": None,
                }
            )
    return rows


def fetch_showtimes(
    venue_key: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Fetch UTC showtime rows for one Cine Starz venue."""
    start = start_date or datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = end_date or start + timedelta(days=90)
    rows: dict[str, dict[str, Any]] = {}
    date = start
    while date.date() <= end.date():
        url = f"{BASE_URL}/theater/nowplaying?locationKey={venue_key}"
        url += f"&date={date:%Y-%m-%d}"
        try:
            for row in _parse_schedule(_fetch(url), date):
                rows[row["external_id"]] = row
        except urllib.error.URLError:
            pass
        date += timedelta(days=1)
    return sorted(rows.values(), key=lambda row: row["showtime"])


def _extract_movie_detail(html_body: str) -> dict[str, Any]:
    """Extract available movie metadata from page JSON-LD."""
    result: dict[str, Any] = {}
    for raw_json in _JSON_LD_RE.findall(html_body):
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("@type") == "Movie":
            for source_key, result_key in (
                ("Description", "description"),
                ("Image", "poster_url"),
                ("ContentRating", "rating"),
            ):
                if isinstance(value := data.get(source_key), str) and value:
                    result[result_key] = value
            if isinstance(date_created := data.get("DateCreated"), str):
                if year_match := re.search(r"\b(\d{4})\b", date_created):
                    result["release_year"] = int(year_match.group(1))
        if data.get("@type") != "ItemList":
            continue
        items = data.get("ItemListElement")
        if not isinstance(items, list) or not items or not isinstance(items[0], dict):
            continue
        event = items[0].get("Item")
        work = event.get("WorkPresented") if isinstance(event, dict) else None
        if isinstance(work, dict) and isinstance(duration := work.get("Duration"), str):
            if duration.isdigit():
                result["duration_minutes"] = int(duration)
    return result


class CineStarzSource:
    """Showtime source for Cine Starz locations."""

    async def fetch_showtimes(
        self,
        venue_key: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for one Cine Starz venue."""
        return fetch_showtimes(venue_key, start_date, end_date)

    async def fetch_movie_detail(self, identifier: str) -> dict[str, Any] | None:
        """Fetch optional JSON-LD movie metadata."""
        try:
            result = _extract_movie_detail(_fetch(identifier))
        except urllib.error.URLError:
            return None
        return result or None
