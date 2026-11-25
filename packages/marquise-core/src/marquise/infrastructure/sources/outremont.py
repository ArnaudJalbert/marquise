"""Showtime source for Théâtre Outremont (Ciné-Outremont).

The public ``/cinema/`` listing page only exposes a *date* per screening. The
exact showtimes (and rich film metadata) live in the venue's Tuxedo Billet
ticketing backend, an Angular single-page app whose data is served from a
**Firebase Realtime Database (RTDB)**. This module reads that backend directly
over plain HTTP — no browser required — following the same bootstrap the SPA
itself performs:

1. ``GET https://theatreoutremont.tuxedobillet.com/configuration.json`` — a
   public config blob exposing the Firebase ``apiKey`` and ``databaseURL``.
2. ``POST https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=<apiKey>``
   with ``{"returnSecureToken": true}`` — anonymous Firebase sign-in (the site's
   own read mechanism; ``apiKey`` is a client-side key), returning an ``idToken``.
3. ``GET <databaseURL>/application/configuration/endpoints.json`` filtered by
   host — resolves the venue's ``idChannel``.
4. ``GET <databaseURL>/application-end-user/<idChannel>/reportCategories.json`` —
   category id → name map, used to keep only ``Cinéma`` shows.
5. ``GET <databaseURL>/application-end-user/<idChannel>/shows.json`` — every show,
   each carrying an ``events`` map of ``eventId → epoch-millis`` (the exact
   screening instants, in UTC), plus ``title``, ``uniqueShowId`` (slug),
   ``description`` (HTML), ``subTitles``, and ``images.main`` (poster).

RTDB reads require the ``idToken`` (``?auth=<token>``); the reads themselves
return plain JSON. Firestore is disabled on the project — all data is RTDB.
"""

from __future__ import annotations

import html as html_mod
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

import certifi

from marquise.interface_adapters.mappers import to_aware_utc

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

HOST = "theatreoutremont.tuxedobillet.com"
CONFIG_URL = f"https://{HOST}/configuration.json"
TICKET_BASE = f"https://{HOST}/web/"
SIGNUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp"

_CINEMA_CATEGORY = "cinéma"

_TITLE_PREFIX_RE = re.compile(r"^[^|]*\|\s*")
_ORIGINAL_TITLE_RE = re.compile(r"\(([^)]+)\)\s*$")
_PARAGRAPH_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)
_STRONG_RE = re.compile(r"<strong\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_METADATA_RE = re.compile(
    r"^(?P<countries>.+?)\.\s*"
    r"(?P<year>(?:19|20)\d{2})\.\s*"
    r"(?P<genre>[^.]+?)\.\s*"
    r"(?:(?P<duration>\d+)\s*min\b\.?)?"
    r"(?P<rest>.*)$",
    re.DOTALL,
)
_RATING_RE = re.compile(r"\(([^)]+)\)")
_DIRECTOR_RE = re.compile(r"un film d['e]\s*(.+)$", re.IGNORECASE)


def _fetch_json(url: str, data: bytes | None = None) -> Any:  # noqa: ANN401
    """Fetch a URL and parse the JSON response.

    Args:
        url: The URL to fetch.
        data: Optional POST body bytes (sent as ``application/json``).

    Returns:
        The parsed JSON payload (dict, list, or scalar).
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Marquise/1.0)"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, context=_SSL_CONTEXT) as resp:
        return json.loads(resp.read().decode())


def _bootstrap() -> tuple[str, str, str]:
    """Resolve the RTDB base URL, an auth token, and the venue channel id.

    Performs the same bootstrap the Tuxedo Billet SPA does: read the public
    config, sign in anonymously, then look up the channel for this host.

    Returns:
        A ``(database_url, id_token, channel_id)`` tuple.

    Raises:
        KeyError: If the config or endpoints payloads are missing expected keys.
        ValueError: If no channel is registered for this host.
    """
    config = _fetch_json(CONFIG_URL)
    firebase = config["firebase"]
    api_key = firebase["apiKey"]
    database_url = firebase["databaseURL"].rstrip("/")

    signup_body = json.dumps({"returnSecureToken": True}).encode()
    token_payload = _fetch_json(
        f"{SIGNUP_URL}?key={urllib.parse.quote(api_key)}", data=signup_body
    )
    token = token_payload["idToken"]

    query = urllib.parse.urlencode(
        {"orderBy": '"host"', "equalTo": f'"{HOST}"', "auth": token}
    )
    endpoints = _fetch_json(
        f"{database_url}/application/configuration/endpoints.json?{query}"
    )
    if not endpoints:
        raise ValueError(f"No Tuxedo channel registered for host {HOST!r}")
    entry = next(iter(endpoints.values()))
    channel = entry["idChannel"]

    return database_url, token, channel


def _read_category_names(database_url: str, token: str, channel: str) -> dict[str, str]:
    """Read the ``firstgroup`` report-category id → name map for a channel.

    Args:
        database_url: The RTDB base URL.
        token: A Firebase auth token.
        channel: The channel id.

    Returns:
        A mapping of category id to its (stripped) name.
    """
    node = _fetch_json(
        f"{database_url}/application-end-user/{channel}/reportCategories.json"
        f"?auth={token}"
    )
    first_group = (node or {}).get("firstgroup", {}) or {}
    return {
        cid: (cat.get("name") or "").strip()
        for cid, cat in first_group.items()
        if isinstance(cat, dict)
    }


def _read_shows(database_url: str, token: str, channel: str) -> dict[str, Any]:
    """Read all shows for a channel.

    Args:
        database_url: The RTDB base URL.
        token: A Firebase auth token.
        channel: The channel id.

    Returns:
        A mapping of show id to its show document.
    """
    node = _fetch_json(
        f"{database_url}/application-end-user/{channel}/shows.json?auth={token}"
    )
    return node or {}


def _read_show(
    database_url: str, token: str, channel: str, show_id: str
) -> dict[str, Any] | None:
    """Read a single show document by its RTDB key.

    Args:
        database_url: The RTDB base URL.
        token: A Firebase auth token.
        channel: The channel id.
        show_id: The show's RTDB key.

    Returns:
        The show document, or ``None`` if it does not exist.
    """
    node = _fetch_json(
        f"{database_url}/application-end-user/{channel}/shows/"
        f"{urllib.parse.quote(show_id)}.json?auth={token}"
    )
    return node if isinstance(node, dict) else None


def _clean_title(title: str) -> str:
    """Strip a leading ``"<cadre> | "`` prefix off a show title.

    Args:
        title: The raw show title, e.g. ``"Ciné-Outremont | Blue Velvet"``.

    Returns:
        The title without its category prefix, e.g. ``"Blue Velvet"``.
    """
    return _TITLE_PREFIX_RE.sub("", html_mod.unescape(title)).strip()


def _is_cinema(show: dict[str, Any], category_names: dict[str, str]) -> bool:
    """Report whether a show's primary category is ``Cinéma``.

    Args:
        show: A show document.
        category_names: The ``firstgroup`` id → name map.

    Returns:
        ``True`` if the show's ``firstgroup`` category resolves to ``Cinéma``.
    """
    report_categories = show.get("reportCategories") or {}
    first_group_id = report_categories.get("firstgroup")
    name = category_names.get(first_group_id, "")
    return name.strip().lower() == _CINEMA_CATEGORY


def _show_rows(show: dict[str, Any], show_id: str) -> list[dict[str, Any]]:
    """Build one showtime row per event in a show.

    Args:
        show: A show document.
        show_id: The show's RTDB key (used as the enrichment ``identifier``).

    Returns:
        A list of plain showtime dicts (unfiltered by date range).
    """
    slug = show.get("uniqueShowId")
    if not slug:
        return []
    title = _clean_title(show.get("title", ""))
    if not title:
        return []
    ticket_url = f"{TICKET_BASE}{slug}"

    rows: list[dict[str, Any]] = []
    for event_id, millis in (show.get("events") or {}).items():
        if not isinstance(millis, (int, float)):
            continue
        showtime = datetime.fromtimestamp(millis / 1000, tz=UTC).isoformat()
        rows.append(
            {
                "movie_title": title,
                "showtime": showtime,
                "identifier": show_id,
                "external_id": event_id,
                "ticket_url": ticket_url,
                "room": None,
                "language": None,
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
    now = datetime.now(tz=UTC)
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
    """Fetch showtimes for Théâtre Outremont (Ciné-Outremont).

    Reads the Tuxedo Billet Firebase backend (see the module docstring),
    keeps only ``Cinéma`` shows, and emits one row per screening event with
    its exact UTC instant.

    Args:
        start_date: Earliest showtime to include (inclusive).
        end_date: Latest showtime to include (inclusive).

    Returns:
        A list of plain dicts with keys ``movie_title``, ``showtime``,
        ``identifier``, ``external_id``, ``ticket_url``, ``room``,
        ``language``.
    """
    range_start, range_end = _get_date_range(start_date, end_date)
    range_start = to_aware_utc(range_start)
    range_end = to_aware_utc(range_end)

    database_url, token, channel = _bootstrap()
    category_names = _read_category_names(database_url, token, channel)
    shows = _read_shows(database_url, token, channel)

    rows: list[dict[str, Any]] = []
    for show_id, show in shows.items():
        if not isinstance(show, dict) or not _is_cinema(show, category_names):
            continue
        for row in _show_rows(show, show_id):
            showtime = datetime.fromisoformat(row["showtime"])
            if range_start <= showtime <= range_end:
                rows.append(row)

    rows.sort(key=lambda row: row["showtime"])
    return rows


def _split_names(raw: str) -> list[str]:
    """Split a comma/``et``-separated list of names into a clean list.

    Args:
        raw: A raw list such as ``"Jean-Pierre et Luc Dardenne"`` or
            ``"Kyle MacLachlan, Isabella Rossellini"``.

    Returns:
        A list of trimmed, non-empty names.
    """
    parts = re.split(r"\s*,\s*|\s+et\s+", raw)
    return [p.strip() for p in parts if p.strip()]


def _extract_directors(show: dict[str, Any]) -> list[str]:
    """Extract director names from a show's ``subTitles``.

    Args:
        show: A show document.

    Returns:
        A list of director names (possibly empty).
    """
    for subtitle in show.get("subTitles") or []:
        text = html_mod.unescape((subtitle.get("title") or "").strip())
        match = _DIRECTOR_RE.match(text)
        if match:
            return _split_names(match.group(1))
    return []


def _paragraph_texts(html: str) -> list[tuple[str, str]]:
    """Split description HTML into ``(inner_html, plain_text)`` paragraph pairs.

    Args:
        html: The show ``description`` HTML.

    Returns:
        A list of ``(inner_html, plain_text)`` tuples for each non-empty
        ``<p>`` block, in document order.
    """
    pairs: list[tuple[str, str]] = []
    for inner in _PARAGRAPH_RE.findall(html):
        text = " ".join(html_mod.unescape(re.sub(r"<[^>]+>", " ", inner)).split())
        if text:
            pairs.append((inner, text))
    return pairs


def _parse_metadata_line(text: str, result: dict[str, Any]) -> None:
    """Parse the ``Countries. Year. Genre. NNN min. (Rating)`` line into *result*.

    Args:
        text: The plain text of the metadata paragraph.
        result: The enrichment dict to populate in place.
    """
    match = _METADATA_RE.match(text)
    if not match:
        return

    # The countries capture may be preceded by a language-version sentence
    # (e.g. "Version originale avec sous-titres français. États-Unis"); keep
    # only the last period-delimited segment, since country names never
    # contain a period.
    countries = _split_names(match.group("countries").rsplit(".", 1)[-1])
    if countries:
        result["origin_countries"] = countries

    result["release_year"] = int(match.group("year"))

    genres = [g.strip() for g in re.split(r"[/,]", match.group("genre")) if g.strip()]
    if genres:
        result["genres"] = genres

    if match.group("duration"):
        result["duration_minutes"] = int(match.group("duration"))

    rating_match = _RATING_RE.search(match.group("rest"))
    if rating_match:
        result["rating"] = rating_match.group(1).strip()


def _extract_outremont_film_detail(show: dict[str, Any]) -> dict[str, Any]:
    """Extract enriched movie metadata from a Théâtre Outremont show document.

    The ``description`` HTML is paragraph-delimited; paragraphs are classified
    by content (a bold title line, a metadata line containing a year, an
    ``Avec …`` cast line, and prose), so extra spacer paragraphs are ignored.

    Args:
        show: A show document.

    Returns:
        A flat dict of movie metadata (may be empty).
    """
    result: dict[str, Any] = {}

    poster = (show.get("images") or {}).get("main")
    if poster:
        result["poster_url"] = poster

    directors = _extract_directors(show)
    if directors:
        result["directors"] = directors

    paragraphs = _paragraph_texts(show.get("description", ""))
    synopsis: list[str] = []
    for inner, text in paragraphs:
        if _STRONG_RE.search(inner):
            original = _ORIGINAL_TITLE_RE.search(text)
            if original:
                result["original_title"] = original.group(1).strip()
            continue
        if text.lower().startswith("avec "):
            cast = _split_names(text[len("avec ") :])
            if cast:
                result["cast"] = cast
            continue
        if "release_year" not in result and _YEAR_RE.search(text):
            _parse_metadata_line(text, result)
            continue
        synopsis.append(text)

    if synopsis:
        result["description"] = " ".join(synopsis).strip()

    return result


class OutremontSource:
    """Showtime source for Théâtre Outremont (single venue)."""

    async def fetch_showtimes(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for Théâtre Outremont.

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
        """Fetch enriched movie metadata for a Théâtre Outremont screening.

        Reads the single show document identified by ``identifier`` (the
        show's Firebase key, as returned in a showtime row's ``identifier``
        field) and parses its metadata.

        Args:
            identifier: The show's RTDB key.

        Returns:
            A dict of movie metadata, or ``None`` if the show cannot be read
            or yields no metadata.
        """
        try:
            database_url, token, channel = _bootstrap()
            show = _read_show(database_url, token, channel, identifier)
        except urllib.error.HTTPError:
            return None
        if show is None:
            return None
        result = _extract_outremont_film_detail(show)
        return result or None
