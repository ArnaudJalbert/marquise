"""Showtime source for Cinémas Beaubien, du Parc, and du Musée.

Fetches from https://cinemacinema.ca/en/schedule/__data.json
and parses the SvelteKit devalue format.
"""

from __future__ import annotations

import asyncio
import json
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

SCHEDULE_URL = "https://cinemacinema.ca/en/schedule/__data.json"

CINEMA_MAP: dict[int, str] = {
    1: "beaubien",
    2: "du-parc",
    3: "du-musee",
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
            A list of plain dicts with keys ``movie_title``, ``showtime``.

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

                title = rep.get("titre") or film.get("titre", "Untitled")

                results.append(
                    {
                        "movie_title": title,
                        "showtime": showtime,
                    }
                )

        return results
