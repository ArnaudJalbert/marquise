#!/usr/bin/env python3
"""Scrape movie schedules from cinemapublic.ca, using the project's source module.

Usage:
    python bin/scrape_cinemapublic.py                       # both venues
    python bin/scrape_cinemapublic.py --venue casa-d-italia # Casa d'Italia
    python bin/scrape_cinemapublic.py --venue livart        # Livart
"""

from __future__ import annotations

import argparse
from typing import Any

from marquise.infrastructure.sources.cinemapublic.gateways.source import (
    VENUE_MAP,
    fetch_showtimes,
)

VENUE_NAMES: dict[str, str] = VENUE_MAP


def display(results: list[dict[str, Any]], venue_label: str) -> None:
    """Print formatted showtimes.

    Args:
        results: List of showtime dicts from ``fetch_showtimes``.
        venue_label: Display name for the venue.
    """
    if not results:
        print(f"  No showtimes found for {venue_label}.")
        return

    print(f"\n{'=' * 72}")
    print(f"  {venue_label}")
    print(f"{'=' * 72}")

    for r in results:
        title = r["movie_title"]
        showtime = r["showtime"]
        price = f"${r['price']:.0f}" if r["price"] is not None else ""
        sold = " [SOLD OUT]" if r.get("is_sold_out") else ""

        print(f"  {showtime}  {title}{sold}  {price}")


def main() -> None:
    """Entry point for ``python bin/scrape_cinemapublic.py``."""
    parser = argparse.ArgumentParser(
        description="Scrape movie schedules from cinemapublic.ca"
    )
    parser.add_argument(
        "--venue",
        "-v",
        choices=list(VENUE_NAMES.keys()) + ["all"],
        default="all",
        help="Which venue to scrape (default: all)",
    )
    args = parser.parse_args()

    venues = list(VENUE_NAMES.keys()) if args.venue == "all" else [args.venue]

    for venue in venues:
        results = fetch_showtimes(venue=venue)
        display(results, VENUE_NAMES[venue])


if __name__ == "__main__":
    main()
