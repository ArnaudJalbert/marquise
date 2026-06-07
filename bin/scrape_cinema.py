#!/usr/bin/env python3
"""Scrape movie schedules from cinemacinema.ca, using the project's source module.

Usage:
    python bin/scrape_cinema.py                                     # all cinemas, today
    python bin/scrape_cinema.py --cinema beaubien                   # only Beaubien
    python bin/scrape_cinema.py --start-date 2026-06-08             # from June 8 onward
    python bin/scrape_cinema.py --start-date 2026-06-08 --end-date 2026-06-14
"""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from marquise.infrastructure.sources.cinemacinema.gateways.source import (
    _extract_date_from_iso,
    _fetch_schedule,
    _fetch_schedules_for_dates,
    _is_in_range,
    _parse_time,
)

CINEMA_SLUGS: dict[str, int] = {
    "beaubien": 1,
    "du-parc": 2,
    "du-musee": 3,
}

CINEMA_DISPLAY_NAMES: dict[int, str] = {
    1: "Cinéma Beaubien",
    2: "Cinéma du Parc",
    3: "Cinéma du Musée",
}


def _collect_all_representations(
    cinema_filter: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[tuple[int, str], list[dict]]:
    """Fetch and group representations by (cinema_id, date_key).

    Args:
        cinema_filter: Optional cinema slug to filter by.
        start_date: Earliest date (inclusive, compared to midnight).
        end_date: Latest date (inclusive).

    Returns:
        Dict mapping ``(cinema_id, date_key)`` to a list of
        ``{"film": …, "rep": …}`` entries.
    """
    selected_ids: set[int] = set()
    if cinema_filter and cinema_filter in CINEMA_SLUGS:
        selected_ids.add(CINEMA_SLUGS[cinema_filter])

    initial = _fetch_schedule()
    cm_dates: list[str] = initial.get("cmDates", [])
    if not cm_dates:
        return {}

    if start_date is not None or end_date is not None:
        filtered_dates = [
            d
            for d in cm_dates
            if _is_in_range(_extract_date_from_iso(d), start_date, end_date)
        ]
    else:
        filtered_dates = cm_dates

    if not filtered_dates:
        return {}

    today_str = _extract_date_from_iso(cm_dates[0])
    needs_init = _is_in_range(today_str, start_date, end_date)

    all_films: list[dict[str, Any]] = []
    if needs_init:
        all_films.extend(initial.get("filmsRepresentations", []))

    remaining = [d for d in filtered_dates if _extract_date_from_iso(d) != today_str]
    if remaining:
        extra_results = asyncio.run(
            _fetch_schedules_for_dates([_extract_date_from_iso(d) for d in remaining])
        )
        for extra in extra_results:
            all_films.extend(extra.get("filmsRepresentations", []))

    grouped: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for film in all_films:
        cinema_id: int = film.get("cinema_id")
        if selected_ids and cinema_id not in selected_ids:
            continue
        reps = film.get("representations", [])
        if not reps:
            continue
        for rep in reps:
            date_str: str = rep.get("representation_date", "")
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            date_key = date_obj.strftime("%a %b %d %Y")
            grouped[(cinema_id, date_key)].append({"film": film, "rep": rep})

    return grouped


def display(data: dict[tuple[int, str], list[dict]]) -> None:
    """Print formatted showtimes grouped by cinema and date.

    Args:
        data: The dict returned by ``_collect_all_representations``.
    """
    if not data:
        print("No showtimes found.")
        return

    for cinema_id, date_key in sorted(data, key=lambda x: (x[0], x[1])):
        cinema_name = CINEMA_DISPLAY_NAMES.get(cinema_id, f"Cinema #{cinema_id}")
        print(f"\n{'=' * 72}")
        print(f"  {cinema_name} — {date_key}")
        print(f"{'=' * 72}")

        entries = data[(cinema_id, date_key)]
        entries.sort(key=lambda e: e["rep"].get("heure_debut", ""))

        for entry in entries:
            rep = entry["rep"]
            film = entry["film"]
            time_str = _parse_time(rep.get("heure_debut", "??"))
            title = rep.get("titre", film.get("titre", "?"))
            version = rep.get("version", film.get("version", ""))
            room = rep.get("salle", "")
            fmt = rep.get("format", "")

            parts = [f"  {time_str:>8}  {title}"]
            if version:
                parts.append(f"[{version}]")
            if fmt:
                parts.append(f"({fmt})")
            if room:
                parts.append(f"Salle {room}")
            print(" ".join(parts))


def main() -> None:
    """Entry point for ``python bin/scrape_cinema.py``."""
    parser = argparse.ArgumentParser(
        description="Scrape movie schedules from cinemacinema.ca"
    )
    parser.add_argument(
        "--cinema",
        "-c",
        choices=list(CINEMA_SLUGS.keys()) + ["all"],
        default="all",
        help="Which cinema to scrape (default: all)",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=None,
        help="Start date (YYYY-MM-DD, inclusive)",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=None,
        help="End date (YYYY-MM-DD, inclusive)",
    )
    args = parser.parse_args()

    cinema_filter = None if args.cinema == "all" else args.cinema

    start_dt = (
        datetime.combine(args.start_date, datetime.min.time())
        if args.start_date
        else None
    )
    end_dt = (
        datetime.combine(args.end_date, datetime.max.time()) if args.end_date else None
    )

    grouped = _collect_all_representations(cinema_filter, start_dt, end_dt)
    display(grouped)


if __name__ == "__main__":
    main()
