"""Showtime source for Cinémas Beaubien, du Parc, and du Musée.

Fetches from https://cinemacinema.ca/en/schedule/__data.json
and parses the SvelteKit devalue format.
"""

from __future__ import annotations

import asyncio
import html
import json
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

SCHEDULE_URL = "https://cinemacinema.ca/en/schedule/__data.json"
FILM_DETAIL_TPL = "https://cinemacinema.ca/en/films/{slug}/__data.json"

CINEMA_MAP: dict[int, str] = {
    1: "beaubien",
    2: "du-parc",
    3: "du-musee",
}

_TICKET_URL_TEMPLATES: dict[str, str] = {
    "beaubien": "https://billetterie.cinemabeaubien.com/FR/Film-achats.awp?P1={rep_id}&P2=",
    "du-parc": "https://billetterie.cinemaduparc.com/FR/Film-achats.awp?P1={rep_id}&P2=",
    "du-musee": "https://billetterie.cinemadumusee.com/FR/Film-achats.awp?P1={rep_id}&P2=",
}

_ISO_DATE_FORMAT = "%Y-%m-%d"


def _resolve(
    val: Any,  # noqa: ANN401
    data: list,
    depth: int = 0,
) -> Any:  # noqa: ANN401
    if depth > 50:
        return None
    if isinstance(val, int):
        result = data[val]
        if isinstance(result, (dict, list)):
            return _resolve(result, data, depth + 1)
        return result
    if isinstance(val, list):
        return [_resolve(v, data, depth + 1) for v in val]
    if isinstance(val, dict):
        return {k: _resolve(v, data, depth + 1) for k, v in val.items()}
    return val


def _parse_sveltekit_data(raw: str) -> dict:
    """Parse SvelteKit devalue ``__data.json`` into a flat dict.

    Collects ``filmsRepresentations`` and ``cmDates`` from any relevant
    node in the response.
    """
    parsed = json.loads(raw)
    result: dict[str, Any] = {}
    for node in parsed.get("nodes", []):
        if node is None or not isinstance(node, dict):
            continue
        data = node.get("data", [])
        if not data or not isinstance(data, list):
            continue
        root = _resolve(data[0], data)
        if isinstance(root, dict):
            if "filmsRepresentations" in root:
                result["filmsRepresentations"] = root["filmsRepresentations"]
            if "cmDates" in root:
                result["cmDates"] = root["cmDates"]
    return result


def _fetch_schedule(date_str: str | None = None) -> dict:
    """Fetch and parse the schedule from cinemacinema.ca.

    Args:
        date_str: An optional ``YYYY-MM-DD`` date string.  When provided,
            only showtimes for that date are returned.

    Returns:
        A dict with ``filmsRepresentations`` and/or ``cmDates`` keys.
    """
    ctx = ssl._create_unverified_context()
    url = SCHEDULE_URL
    if date_str:
        url = f"{SCHEDULE_URL}?date={date_str}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=ctx) as resp:
        raw = resp.read().decode()
    return _parse_sveltekit_data(raw)


def _parse_time(time_str: str) -> str:
    """Normalize a time string to ``HH:MM`` 24-hour format.

    Accepts both 12-hour (``"2:00 PM"``) and 24-hour (``"14:00"``) formats.

    Args:
        time_str: The raw time string.

    Returns:
        A ``HH:MM`` formatted time string.
    """
    time_str = time_str.strip()
    try:
        return datetime.strptime(time_str, "%I:%M %p").strftime("%H:%M")
    except ValueError:
        pass
    return time_str


def _extract_date_from_iso(iso_str: str) -> str:
    """Extract ``YYYY-MM-DD`` from an ISO datetime string."""
    return iso_str[:10]


def _is_in_range(
    date_str: str,
    start_date: datetime | None,
    end_date: datetime | None,
) -> bool:
    """Check whether *date_str* (``YYYY-MM-DD``) falls in [start, end]."""
    dt = datetime.strptime(date_str, _ISO_DATE_FORMAT).replace(tzinfo=timezone.utc)
    if start_date and dt < start_date:
        return False
    if end_date and dt > end_date:
        return False
    return True


async def _fetch_schedules_for_dates(
    date_strings: list[str],
) -> list[dict]:
    """Fetch schedule data for multiple dates concurrently.

    Args:
        date_strings: List of ``YYYY-MM-DD`` date strings.

    Returns:
        A list of parsed result dicts (one per date).
    """
    loop = asyncio.get_running_loop()
    max_workers = min(len(date_strings), 10)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = [
            loop.run_in_executor(executor, _fetch_schedule, d) for d in date_strings
        ]
        return await asyncio.gather(*tasks)


def _ticket_slug(cinema_name: str) -> str:
    """Convert a cinema slug to a billetterie subdomain piece.

    Args:
        cinema_name: One of ``"beaubien"``, ``"du-parc"``, ``"du-musee"``.

    Returns:
        The subdomain piece (e.g. ``"beaubien"``, ``"dupac"``).
    """
    return cinema_name.replace("-", "")


def _ticket_url(cinema_name: str, rep_id: int) -> str | None:
    """Build a ticket purchase URL for a representation.

    Args:
        cinema_name: The cinema slug.
        rep_id: The representation ID.

    Returns:
        The constructed ticket URL, or ``None`` if no template is known.
    """
    tpl = _TICKET_URL_TEMPLATES.get(cinema_name)
    if tpl is None:
        return None
    return tpl.format(rep_id=rep_id)


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split()).strip()


def _extract_film_detail(film: dict) -> dict[str, Any]:
    """Extract enriched movie metadata from a ``cmFilmCurrent`` dict.

    Args:
        film: The raw ``cmFilmCurrent`` dict from the SvelteKit response.

    Returns:
        A flat dict of metadata fields.
    """
    directors: list[str] = []
    raw_directors = film.get("realisateur", "")
    if raw_directors:
        directors = [d.strip() for d in raw_directors.split(",") if d.strip()]

    cast_list: list[str] = []
    raw_cast = film.get("acteurs", "")
    if raw_cast:
        cast_list = [c.strip() for c in raw_cast.split(",") if c.strip()]

    genres: list[str] = []
    for key in ("genre1", "genre2", "genre3"):
        g = film.get(key, "")
        if g:
            genres.append(g)

    origin_countries: list[str] = []
    for key in ("origine1", "origine2", "origine3"):
        c = film.get(key, "")
        if c:
            origin_countries.append(c)

    synopsis_raw = film.get("synopsis", "")
    description = _strip_html(synopsis_raw) if synopsis_raw else None

    return {
        "description": description,
        "directors": directors if directors else None,
        "cast": cast_list if cast_list else None,
        "duration_minutes": film.get("duree"),
        "release_year": film.get("annee"),
        "origin_countries": origin_countries if origin_countries else None,
        "poster_url": film.get("poster_url"),
        "trailer_url": film.get("bande_annonce_url"),
        "genres": genres if genres else None,
        "rating": film.get("classment"),
        "original_title": film.get("original_title"),
    }


class CinemaCinemaSource:
    """Showtime source for Cinémas Beaubien, du Parc, and du Musée."""

    async def fetch_showtimes(
        self,
        cinema_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch showtimes for a cinemacinema.ca cinema.

        When *start_date* and *end_date* are both ``None`` the entire
        available schedule is returned.  Otherwise only dates in
        ``[start_date, end_date]`` are included.

        Args:
            cinema_name: One of ``"beaubien"``, ``"du-parc"``, ``"du-musee"``.
            start_date: Earliest date to include (inclusive, time portion
                is compared against midnight of each day).
            end_date: Latest date to include (inclusive).

        Returns:
            A list of plain dicts with keys ``movie_title``, ``showtime``,
            ``identifier``, ``external_id``, ``ticket_url``, ``room``,
            ``language``.

        Raises:
            ValueError: If ``cinema_name`` is not a recognised slug.
        """
        if cinema_name not in CINEMA_MAP.values():
            raise ValueError(
                f"cinema_name must be one of {set(CINEMA_MAP.values())}, "
                f"got '{cinema_name}'"
            )

        target_id = next(cid for cid, slug in CINEMA_MAP.items() if slug == cinema_name)

        # ------------------------------------------------------------------
        # 1.  Fetch the schedule (no date) to obtain the available dates and
        #     today's representations.
        # ------------------------------------------------------------------
        initial = _fetch_schedule()
        cm_dates: list[str] = initial.get("cmDates", [])
        if not cm_dates:
            return []

        # ------------------------------------------------------------------
        # 2.  Filter the date picker to the requested range.
        # ------------------------------------------------------------------
        if start_date is not None or end_date is not None:
            filtered = [
                d
                for d in cm_dates
                if _is_in_range(_extract_date_from_iso(d), start_date, end_date)
            ]
        else:
            filtered = cm_dates

        if not filtered:
            return []

        # ------------------------------------------------------------------
        # 3.  Determine which date the no-param fetch returned so we can
        #     avoid re-fetching it.  The no-param fetch always returns
        #     today (the first entry in the unfiltered cmDates array).
        # ------------------------------------------------------------------
        today_str = _extract_date_from_iso(cm_dates[0]) if cm_dates else ""
        needs_init = _is_in_range(today_str, start_date, end_date)

        # ------------------------------------------------------------------
        # 4.  Collect ``filmsRepresentations`` from every date in range.
        # ------------------------------------------------------------------
        all_films: list[dict[str, Any]] = []

        if needs_init:
            all_films.extend(initial.get("filmsRepresentations", []))

        remaining = [d for d in filtered if _extract_date_from_iso(d) != today_str]
        if remaining:
            extra_results = await _fetch_schedules_for_dates(
                [_extract_date_from_iso(d) for d in remaining]
            )
            for extra in extra_results:
                all_films.extend(extra.get("filmsRepresentations", []))

        if not all_films:
            return []

        # ------------------------------------------------------------------
        # 5.  Flatten and normalise representations into plain dicts.
        # ------------------------------------------------------------------
        results: list[dict[str, Any]] = []
        for film in all_films:
            cinema_id: int = film.get("cinema_id")
            if cinema_id != target_id:
                continue
            film_slug: str = film.get("slug", "")
            reps = film.get("representations", [])
            if not reps:
                continue
            for rep in reps:
                date_str: str = rep.get("representation_date", "")
                time_str = _parse_time(rep.get("heure_debut", ""))
                if not date_str or not time_str:
                    continue
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                showtime = date_obj.strftime(_ISO_DATE_FORMAT) + "T" + time_str

                title = film.get("titre", "Untitled")
                representation_id: int = rep.get("representation_id", 0)
                salle: int | None = rep.get("salle")
                version: str | None = rep.get("version")

                results.append(
                    {
                        "movie_title": title,
                        "showtime": showtime,
                        "identifier": film_slug,
                        "external_id": str(representation_id),
                        "ticket_url": _ticket_url(cinema_name, representation_id),
                        "room": str(salle) if salle is not None else None,
                        "language": version,
                    }
                )

        return results

    async def fetch_movie_detail(
        self,
        slug: str,
    ) -> dict[str, Any] | None:
        """Fetch enriched movie metadata from the film detail page.

        Args:
            slug: The film slug (e.g. ``"salo-or-the-120-days-of-sodom-1958"``).

        Returns:
            A dict of movie metadata, or ``None`` if not found.
        """
        url = FILM_DETAIL_TPL.format(slug=slug)
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                raw = resp.read().decode()
        except urllib.error.HTTPError:
            return None

        parsed = json.loads(raw)
        for node in parsed.get("nodes", []):
            if node is None or not isinstance(node, dict):
                continue
            data = node.get("data", [])
            if not data or not isinstance(data, list):
                continue
            root = _resolve(data[0], data)
            if isinstance(root, dict) and "cmFilmCurrent" in root:
                film = root["cmFilmCurrent"]
                if not isinstance(film, dict):
                    return None
                return _extract_film_detail(film)

        return None
