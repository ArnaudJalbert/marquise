"""Showtime source for Cinémathèque québécoise.

Fetches from the OmniWeb ticketing portal at
``https://omniwebticketing6.com/cinematheque/`` (the cinema's own
``cinematheque.qc.ca`` site is served behind a Cloudflare challenge that
blocks automated scraping, but its ticketing backend is not).

Each day's schedule page (``?schdate=YYYY-MM-DD``) embeds the full
programming for that date as a JavaScript object literal
(``var gMovieData = {...};``), keyed by an opaque film code, plus a
``<select id="calendar">`` listing every other date with programming.

The ticketing payload omits year and people. The cinema website's film cards
link ticket modals to detail pages through performance IDs; those pages supply
the missing identity evidence when available. Ticketing data remains the fallback.
"""

from __future__ import annotations

import html
import http.client
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

import certifi

from marquise.infrastructure.sources._timezone import montreal_local_to_utc_iso

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

BASE_URL = "https://omniwebticketing6.com/cinematheque/"
CINEMA_URL = "https://www.cinematheque.qc.ca/en/cinema/"

_MOVIE_DATA_RE = re.compile(r"var gMovieData\s*=\s*(\{.*?\})\s*</script>", re.DOTALL)
_DATE_OPTION_RE = re.compile(r'<option value="(\d{4}-\d{2}-\d{2})">')
_LANGUAGE_RE = re.compile(r"\((VO[A-Z]{0,5}|VF|VA)\)\s*$")
_RUNTIME_RE = re.compile(r"(?:(\d+)\s*hr)?\s*(?:(\d+)\s*min)?")
_FETCH_ATTEMPTS = 3
_TIMEOUT_SECONDS = 15

_ARTICLE_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.DOTALL)
_DETAIL_LINK_RE = re.compile(r'href="(/en/cinema/[^"?#]+/)"')
_MODAL_RE = re.compile(r"modal-tickets-\d+")
_FACT_RE = re.compile(
    r'<div class="color-black-60 text-shorter line-height-compressed">'
    r"([^<]+)</div>\s*<div[^>]*>(.*?)</div>",
    re.DOTALL,
)


class _TicketModals(HTMLParser):
    """Read each modal's dated ticket performance IDs."""

    def __init__(self) -> None:
        """Initialize the current modal stack and performance links."""
        super().__init__()
        self.divs: list[str | None] = []
        self.modals: dict[tuple[str, str], set[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Read ticket links inside provider ticket modals."""
        values = dict(attrs)
        if tag == "div":
            modal = values.get("data-id") or ""
            self.divs.append(
                modal
                if _MODAL_RE.fullmatch(modal)
                else self.divs[-1]
                if self.divs
                else None
            )
        if not self.divs or not self.divs[-1]:
            return
        target = values.get("href") or values.get("data-href") or ""
        url = urlsplit(target)
        if url.hostname not in {"omniwebticketing.com", "omniwebticketing6.com"}:
            return
        if url.path.rstrip("/") != "/cinematheque":
            return
        query = parse_qs(url.query)
        for date in query.get("schdate", []):
            for performance in query.get("perfix", []):
                self.modals.setdefault((date, performance), set()).add(self.divs[-1])

    def handle_endtag(self, tag: str) -> None:
        """Leave a modal when its containing div closes."""
        if tag == "div" and self.divs:
            self.divs.pop()


def find_detail_url(
    index_html: str, performances: set[tuple[str, str]], base_url: str
) -> str | None:
    """Resolve a unique film card through its ticket modal, never a title guess."""
    parser = _TicketModals()
    parser.feed(index_html)
    modals = set().union(*(parser.modals.get(key, set()) for key in performances))
    urls: set[str] = set()
    for article in _ARTICLE_RE.findall(index_html):
        if modals.intersection(_MODAL_RE.findall(article)):
            urls.update(
                urljoin(base_url, path) for path in _DETAIL_LINK_RE.findall(article)
            )
    return next(iter(urls)) if len(urls) == 1 else None


def extract_detail(detail_html: str) -> dict:
    """Read labelled year, people and runtime facts from a cinema film page."""
    facts = {
        label: " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())
        for label, value in _FACT_RE.findall(detail_html)
    }
    result: dict = {}
    for label, field in (("Directed by", "directors"), ("Actors", "cast")):
        names = [
            name.strip() for name in facts.get(label, "").split(",") if name.strip()
        ]
        if names:
            result[field] = names
    year = facts.get("Year", "")
    if re.fullmatch(r"\d{4}", year) and int(year) > 0:
        result["release_year"] = int(year)
    duration = re.fullmatch(r"(\d+)\s*min", facts.get("Duration", ""))
    if duration and int(duration.group(1)) > 0:
        result["duration_minutes"] = int(duration.group(1))
    return result


def _fetch(url: str) -> str:
    """Fetch a URL with SSL verification and a spoofed User-Agent.

    Retry a timed-out response up to three attempts, with 0.5s and 1s delays,
    so one slow page does not fail the import. Exhausted retries propagate.

    Args:
        url: The URL to fetch.

    Returns:
        The response body as a string.

    Raises:
        TimeoutError: When every attempt times out.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Marquise/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(1, _FETCH_ATTEMPTS):
        try:
            return _read(req)
        except TimeoutError:
            time.sleep(0.5 * attempt)
    return _read(req)


def _read(req: urllib.request.Request) -> str:
    """Send one request with a ``_TIMEOUT_SECONDS`` socket timeout.

    Args:
        req: The prepared request.

    Returns:
        The response body as a string.
    """
    with urllib.request.urlopen(
        req, context=_SSL_CONTEXT, timeout=_TIMEOUT_SECONDS
    ) as resp:
        return resp.read().decode()


def _extract_movie_data(html: str) -> dict[str, Any]:
    """Extract the ``gMovieData`` object embedded in a schedule page.

    Args:
        html: The full page HTML for a given ``schdate``.

    Returns:
        A dict mapping film code to its film/schedule data, or an empty
        dict if the page has no schedule for that date.
    """
    match = _MOVIE_DATA_RE.search(html)
    if not match:
        return {}
    return json.loads(match.group(1))


def _extract_available_dates(html: str) -> list[str]:
    """Extract the list of other dates with programming from a schedule page.

    Args:
        html: The full page HTML for a given ``schdate``.

    Returns:
        A list of ``YYYY-MM-DD`` strings for other available dates.
    """
    return _DATE_OPTION_RE.findall(html)


def _split_title_and_language(title: str) -> tuple[str, str | None]:
    """Read a provider version marker while preserving the source title.

    Args:
        title: The film title, e.g. ``"Romería (VOSTF)"``.

    Returns:
        A ``(source_title, marker)`` tuple, preserving screening annotations.
        ``marker`` is ``None`` if the title has no such marker, in which
        case ``source_title`` is the title unchanged.
    """
    match = _LANGUAGE_RE.search(title)
    if not match:
        return title, None
    return title, match.group(1)


def _parse_runtime(run_time_str: str | None) -> int | None:
    """Parse a runtime string like ``"1 hr 27 min"`` into minutes.

    Args:
        run_time_str: The runtime string, or ``None``.

    Returns:
        Minutes as an integer, or ``None`` if unparseable.
    """
    if not run_time_str:
        return None
    match = _RUNTIME_RE.search(run_time_str)
    if not match or not (match.group(1) or match.group(2)):
        return None
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    return hours * 60 + minutes


def _parse_movie_data(
    movie_data: dict[str, Any], date_str: str
) -> list[dict[str, Any]]:
    """Flatten a ``gMovieData`` dict into showtime rows.

    Args:
        movie_data: The parsed ``gMovieData`` object for one date.
        date_str: The ``schdate`` the data was fetched for (fallback date).

    Returns:
        A list of plain dicts with keys ``movie_title``, ``showtime``,
        ``identifier``, ``external_id``, ``ticket_url``, ``room``,
        ``language``.
    """
    rows: list[dict[str, Any]] = []
    for code, film in movie_data.items():
        raw_title = html.unescape(film.get("title") or "")
        if not raw_title.strip():
            continue
        title, language = _split_title_and_language(raw_title)
        for aud in (film.get("schAuds") or {}).values():
            room = aud.get("name")
            for group_key in ("schPerfsReserved", "schPerfsGeneral"):
                for perf in (aud.get(group_key) or {}).values():
                    start_time = perf.get("startTime")
                    if not start_time:
                        continue
                    perf_date = perf.get("schDateStr") or date_str
                    link_str = perf.get("linkStr")
                    perf_ix = perf.get("perfIx")
                    rows.append(
                        {
                            "movie_title": title,
                            "showtime": montreal_local_to_utc_iso(
                                perf_date, start_time
                            ),
                            "identifier": f"{perf_date}|{code}",
                            "external_id": str(perf_ix) if perf_ix else None,
                            "ticket_url": urljoin(BASE_URL, link_str)
                            if link_str
                            else None,
                            "room": room,
                            "language": language,
                        }
                    )
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
    """Fetch showtimes for Cinémathèque québécoise.

    Fetches today's schedule page to discover both today's programming and
    the list of other dates with programming, then fetches each additional
    in-range date concurrently.

    Args:
        start_date: Earliest showtime to include (inclusive).
        end_date: Latest showtime to include (inclusive).

    Returns:
        A list of plain dicts with keys ``movie_title``, ``showtime``,
        ``identifier``, ``external_id``, ``ticket_url``, ``room``,
        ``language``.
    """
    range_start, range_end = _get_date_range(start_date, end_date)
    today_str = datetime.now().strftime("%Y-%m-%d")

    initial_html = _fetch(f"{BASE_URL}?schdate={today_str}")
    other_dates = _extract_available_dates(initial_html)

    ordered_dates: list[str] = []
    seen: set[str] = set()
    for date_str in [today_str, *other_dates]:
        if date_str not in seen:
            seen.add(date_str)
            ordered_dates.append(date_str)

    range_start_date = range_start.date()
    range_end_date = range_end.date()

    def _in_range(date_str: str) -> bool:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        return range_start_date <= dt <= range_end_date

    dates_to_fetch = [d for d in ordered_dates if _in_range(d)]

    results: list[dict[str, Any]] = []

    if today_str in dates_to_fetch:
        results.extend(_parse_movie_data(_extract_movie_data(initial_html), today_str))
        dates_to_fetch = [d for d in dates_to_fetch if d != today_str]

    if dates_to_fetch:

        def _fetch_one(date_str: str) -> list[dict[str, Any]]:
            html = _fetch(f"{BASE_URL}?schdate={date_str}")
            return _parse_movie_data(_extract_movie_data(html), date_str)

        with ThreadPoolExecutor(max_workers=min(len(dates_to_fetch), 10)) as executor:
            futures = [executor.submit(_fetch_one, d) for d in dates_to_fetch]
            for future in futures:
                try:
                    results.extend(future.result())
                except urllib.error.HTTPError:
                    continue

    results.sort(key=lambda row: row["showtime"])
    return results


def _extract_cinematheque_film_detail(film: dict[str, Any]) -> dict[str, Any]:
    """Extract enriched movie metadata from a ``gMovieData`` film entry.

    Args:
        film: One film's entry from ``gMovieData``.

    Returns:
        A flat dict of movie metadata.
    """
    result: dict[str, Any] = {}

    synopsis = film.get("synopsis")
    if isinstance(synopsis, list) and synopsis:
        description = " ".join(str(part) for part in synopsis).strip()
        if description:
            result["description"] = description
    elif isinstance(synopsis, str) and synopsis.strip():
        result["description"] = synopsis.strip()

    duration_minutes = _parse_runtime(film.get("runTimeStr"))
    if duration_minutes is not None:
        result["duration_minutes"] = duration_minutes

    rating_reason = film.get("ratingReason")
    if rating_reason and rating_reason.strip():
        result["rating"] = rating_reason.strip()

    poster_file = film.get("posterFile")
    if poster_file:
        result["poster_url"] = urljoin(BASE_URL, poster_file)

    return result


class CinemathequeSource:
    """Showtime source for Cinémathèque québécoise (single venue)."""

    async def fetch_showtimes(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for Cinémathèque québécoise.

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
        """Fetch ticketing facts and recover evidence from the linked cinema page.

        Args:
            identifier: A ``"YYYY-MM-DD|<film code>"`` string as returned in
                a showtime row's ``identifier`` field.

        Returns:
            A dict of movie metadata, or ``None`` if the film cannot be
            found on that date's schedule page.
        """
        date_str, _, code = identifier.partition("|")
        if not date_str or not code:
            return None
        try:
            html = _fetch(f"{BASE_URL}?schdate={date_str}")
        except OSError:
            return None
        movie_data = _extract_movie_data(html)
        film = movie_data.get(code)
        if not film:
            return None
        result = _extract_cinematheque_film_detail(film)
        performances = {
            (perf.get("schDateStr") or date_str, str(perf["perfIx"]))
            for aud in (film.get("schAuds") or {}).values()
            for group in ("schPerfsReserved", "schPerfsGeneral")
            for perf in (aud.get(group) or {}).values()
            if perf.get("perfIx")
        }
        if performances:
            try:
                index_html = _fetch(CINEMA_URL)
                detail_url = find_detail_url(index_html, performances, CINEMA_URL)
                if detail_url:
                    result.update(extract_detail(_fetch(detail_url)))
            except (OSError, http.client.HTTPException):
                pass  # The ticketing facts remain usable if the website is unavailable.
        return result or None
