"""Showtime source for Cineplex theatres.

Fetches from the Cineplex theatrical API
(``https://apis.cineplex.com/prod/cpx/theatrical/api/v1``) and scrapes
movie detail pages for enriched metadata.
"""

from __future__ import annotations

import html as html_mod
import json
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

import certifi

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

SHOWTIMES_URL = "https://apis.cineplex.com/prod/cpx/theatrical/api/v1/showtimes"
MOVIE_DETAIL_TPL = "https://www.cineplex.com/movie/{slug}"
HOMEPAGE_URL = "https://www.cineplex.com/"

# Public Azure API Management subscription key embedded in Cineplex's own
# web frontend (cineplex.com ships it in plain JS and sends it on every
# anonymous request). The theatrical API began returning HTTP 401 for
# keyless requests, so we send the same anonymous key the website uses.
# Cineplex rotates this key periodically, so it is discovered at runtime
# from the live frontend (see ``_discover_subscription_key``); this baked-in
# value is only a last-resort fallback if discovery fails.
_PUBLIC_SUBSCRIPTION_KEY = "dcdac5601d864addbc2675a2e96cb1f8"

# Locates JS bundle chunks referenced by a Next.js page.
_CHUNK_URL_RE = re.compile(r"/_next/static/chunks/[^\"']+\.js")
# Captures the subscription key sent alongside the theatrical API in the
# minified frontend bundle, e.g.:
#   theatrical/api",c={...headers:{"Ocp-Apim-Subscription-Key":"<32 hex>"
_THEATRICAL_KEY_RE = re.compile(
    r'theatrical[\s\S]{0,400}?Ocp-Apim-Subscription-Key"\s*:\s*"([0-9a-f]{32})"'
)


def _discover_subscription_key() -> str | None:
    """Scrape the current anonymous subscription key from Cineplex's frontend.

    Cineplex ships a public ``Ocp-Apim-Subscription-Key`` in its web bundle and
    rotates it periodically. This downloads the homepage, walks the JS chunks it
    references, and extracts the key sent alongside the theatrical API so we keep
    working across key rotations without any hardcoded value.

    Returns:
        The 32-character subscription key, or ``None`` if it cannot be found
        (e.g. the site is unreachable or its bundle layout changed).
    """
    try:
        html = _fetch_html(HOMEPAGE_URL)
    except urllib.error.URLError:
        return None
    base = HOMEPAGE_URL.rstrip("/")
    # dict.fromkeys preserves order while de-duplicating chunk paths.
    for path in dict.fromkeys(_CHUNK_URL_RE.findall(html)):
        try:
            js = _fetch_html(base + path)
        except urllib.error.URLError:
            continue
        match = _THEATRICAL_KEY_RE.search(js)
        if match:
            return match.group(1)
    return None


def _fetch_json(url: str, api_key: str = "") -> dict[str, Any] | list[Any]:
    """Fetch a JSON endpoint from the Cineplex API.

    Args:
        url: The full URL to fetch.
        api_key: Subscription key for the Cineplex API.

    Returns:
        Parsed JSON.

    Raises:
        urllib.error.HTTPError: On HTTP errors.
    """
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; Marquise/1.0)")
    if api_key:
        req.add_header("Ocp-Apim-Subscription-Key", api_key)
    with urllib.request.urlopen(req, context=_SSL_CONTEXT, timeout=30) as resp:
        raw = resp.read().decode()
    return json.loads(raw)


def _fetch_html(url: str) -> str:
    """Fetch an HTML page from Cineplex.com.

    Args:
        url: The URL to fetch.

    Returns:
        The response body as a string.

    Raises:
        urllib.error.HTTPError: On HTTP errors.
    """
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; Marquise/1.0)")
    with urllib.request.urlopen(req, context=_SSL_CONTEXT, timeout=15) as resp:
        return resp.read().decode()


def _extract_next_data(html: str) -> dict[str, Any] | None:
    """Extract ``__NEXT_DATA__`` JSON from a Next.js page.

    Args:
        html: The full page HTML.

    Returns:
        The parsed ``__NEXT_DATA__`` dict, or ``None`` if not found.
    """
    match = re.search(
        r'<script\s+id="__NEXT_DATA__"[^>]*type="application/json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if match:
        return json.loads(match.group(1))
    return None


def _extract_movie_detail(html: str) -> dict[str, Any] | None:
    """Extract enriched movie metadata from a Cineplex movie detail page.

    Args:
        html: The HTML of the movie detail page.

    Returns:
        A flat dict of movie metadata, or ``None`` if not found.
    """
    data = _extract_next_data(html)
    if not data:
        return None

    page_props = data.get("props", {}).get("pageProps", {})
    movie = page_props.get("movieDetails")
    if not isinstance(movie, dict):
        return None

    directors: list[str] = []
    raw_director = movie.get("director", "")
    if raw_director:
        # Cineplex joins co-director credits with commas or the English "and".
        directors = [
            d.strip() for d in re.split(r",|\s+and\s+", str(raw_director)) if d.strip()
        ]

    cast_list: list[str] = []
    raw_cast = movie.get("starring", "")
    if raw_cast:
        cast_list = [c.strip() for c in str(raw_cast).split(",") if c.strip()]

    genres_raw = movie.get("genres")
    genres: list[str] = (
        [str(g) for g in genres_raw] if isinstance(genres_raw, list) else []
    )

    ratings_raw = movie.get("ratings")
    rating: str | None = None
    if isinstance(ratings_raw, list) and ratings_raw:
        first_rating = ratings_raw[0]
        if isinstance(first_rating, dict):
            rating = first_rating.get("description") or first_rating.get("code")

    synopsis_raw = movie.get("synopsis", "")
    description: str | None = None
    if synopsis_raw:
        description = html_mod.unescape(synopsis_raw)
        description = re.sub(r"<[^>]+>", " ", description)
        description = " ".join(description.split()).strip()

    release_year: int | None = None
    release_date_str = movie.get("releaseDate", "")
    if release_date_str:
        try:
            release_year = datetime.fromisoformat(
                release_date_str.replace("Z", "+00:00")
            ).year
        except (ValueError, TypeError):
            pass

    return {
        "description": description or None,
        "directors": directors if directors else None,
        "cast": cast_list if cast_list else None,
        "duration_minutes": movie.get("runtimeInMinutes"),
        "release_year": release_year,
        "origin_countries": None,
        "poster_url": movie.get("largePosterImageUrl")
        or movie.get("mediumPosterImageUrl"),
        "trailer_url": None,
        "genres": genres if genres else None,
        "rating": rating,
        "original_title": None,
    }


def _is_in_range(
    dt: datetime,
    start_date: datetime | None,
    end_date: datetime | None,
) -> bool:
    """Check whether *dt* falls within [start_date, end_date]."""
    if start_date and dt < start_date:
        return False
    if end_date and dt > end_date:
        return False
    return True


TICKETING_REDIRECT_URL = (
    "https://apis.cineplex.com/prod/ticketing/api/v1/routing/redirect-to-ticketing"
)


def _build_ticket_url(
    location_id: int,
    vista_session_id: int,
    area_code: str,
) -> str:
    """Build a Cineplex ticket/deeplink URL.

    Args:
        location_id: The theatre ID.
        vista_session_id: The Vista session ID.
        area_code: The Vista HO area category code.

    Returns:
        A deeplink URL for ticket purchase.
    """
    return (
        f"{TICKETING_REDIRECT_URL}"
        f"?VistaSessionId={vista_session_id}"
        f"&VISTAHOCategoryCode={area_code}"
        f"&LocationId={location_id}"
        f"&IsSeriesShowtime=False"
    )


def _flatten_showtimes(
    data: list[dict[str, Any]],
    start_date: datetime | None,
    end_date: datetime | None,
) -> list[dict[str, Any]]:
    """Flatten the showtimes API response into a list of plain dicts.

    Args:
        data: The showtimes API response (list of theatre entries).
        start_date: Earliest showtime to include (inclusive).
        end_date: Latest showtime to include (inclusive).

    Returns:
        A list of plain dicts with keys ``movie_title``, ``showtime``,
        ``identifier``, ``external_id``, ``ticket_url``, ``room``,
        ``language``.
    """
    results: list[dict[str, Any]] = []

    for entry in data:
        location_id: int = entry.get("theatreId", 0)
        for date_entry in entry.get("dates", []):
            for movie in date_entry.get("movies", []):
                film_url: str = movie.get("filmUrl", "")
                movie_name: str = movie.get("name", "Untitled")
                movie_lang: str = movie.get("language", "")
                sub_lang: str = movie.get("subtitleLanguage", "")
                if movie_lang and sub_lang:
                    language = f"{movie_lang} ({sub_lang} subtitles)"
                elif movie_lang:
                    language = movie_lang
                else:
                    language = None

                for experience in movie.get("experiences", []):
                    experience_types = experience.get("experienceTypes", [])

                    for session in experience.get("sessions", []):
                        utc_str = session.get("showStartDateTimeUtc", "")
                        if not utc_str:
                            continue

                        try:
                            showtime = datetime.fromisoformat(
                                utc_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            continue

                        if not _is_in_range(showtime, start_date, end_date):
                            continue

                        vista_session_id: int = session.get("vistaSessionId", 0)
                        area_code: str = session.get("areaCode", "0000000001")

                        ticket_url = (
                            session.get("ticketingRedesignUrl")
                            or session.get("ticketingUrl")
                            or _build_ticket_url(
                                location_id=location_id,
                                vista_session_id=vista_session_id,
                                area_code=area_code,
                            )
                        )

                        auditorium: str | None = session.get("auditorium")

                        exp_tag = (
                            "+".join(experience_types) if experience_types else None
                        )

                        results.append(
                            {
                                "movie_title": movie_name,
                                "showtime": showtime.strftime(
                                    "%Y-%m-%dT%H:%M:%S+00:00"
                                ),
                                "identifier": film_url,
                                "external_id": str(vista_session_id),
                                "ticket_url": ticket_url,
                                "room": auditorium,
                                "language": language,
                                "experience": exp_tag,
                            }
                        )

    return results


class CineplexSource:
    """Showtime source for Cineplex theatres."""

    def __init__(self, api_key: str = "") -> None:
        # An explicitly configured key (CINEPLEX_API_KEY) always wins. When it
        # is empty we discover Cineplex's rotating anonymous key at request
        # time; ``_last_known_key`` retains the most recent value (seeded with
        # the baked-in fallback) for when a discovery attempt fails.
        self._configured_api_key = api_key
        self._last_known_key = _PUBLIC_SUBSCRIPTION_KEY

    def _resolve_api_key(self) -> str:
        """Return the subscription key to use for the next API request.

        A configured key is returned as-is. Otherwise the current anonymous key
        is scraped fresh from the Cineplex frontend so we follow key rotations;
        if that fails we reuse the last key that worked.

        Returns:
            The subscription key to send with the request.
        """
        if self._configured_api_key:
            return self._configured_api_key
        discovered = _discover_subscription_key()
        if discovered:
            self._last_known_key = discovered
        return self._last_known_key

    async def fetch_showtimes(
        self,
        location_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for a Cineplex theatre.

        Args:
            location_id: The Cineplex theatre ID (e.g. ``9406`` for
                Banque Scotia Montréal).
            start_date: Earliest showtime to include (inclusive, UTC).
            end_date: Latest showtime to include (inclusive, UTC).

        Returns:
            A list of plain dicts with keys ``movie_title``, ``showtime``,
            ``identifier``, ``external_id``, ``ticket_url``, ``room``,
            ``language``, ``experience``.

        Raises:
            urllib.error.HTTPError: On API errors.
        """
        url = f"{SHOWTIMES_URL}?LocationId={location_id}"
        data = _fetch_json(url, api_key=self._resolve_api_key())
        if not isinstance(data, list):
            return []
        return _flatten_showtimes(data, start_date, end_date)

    async def fetch_movie_detail(
        self,
        slug: str,
    ) -> dict[str, Any] | None:
        """Fetch enriched movie metadata from a Cineplex movie detail page.

        Args:
            slug: The film slug (e.g. ``"the-odyssey"``).

        Returns:
            A dict of movie metadata, or ``None`` if the page cannot be
            fetched or parsed.
        """
        url = MOVIE_DETAIL_TPL.format(slug=slug)
        try:
            html = _fetch_html(url)
        except urllib.error.HTTPError:
            return None
        result = _extract_movie_detail(html)
        return result if result else None
