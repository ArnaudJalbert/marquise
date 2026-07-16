"""Shared Montreal-local to UTC conversion for scraper sources.

Marquise cinemas publish showtimes as Montreal wall-clock time. Sources
that only have a local date/time string (no offset from the provider) must
convert through this helper so every source emits a real, DST-correct UTC
``showtime`` string.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

MONTREAL_TZ = ZoneInfo("America/Toronto")


def montreal_local_to_utc_iso(date_str: str, time_str: str) -> str:
    """Convert a Montreal-local date and time into a real UTC ISO string.

    Args:
        date_str: Date in ``YYYY-MM-DD`` format, Montreal-local.
        time_str: Time in ``HH:MM`` (24-hour) format, Montreal-local.

    Returns:
        A UTC ISO 8601 string (e.g. ``"2026-07-11T23:30:00+00:00"``).
    """
    local_dt = datetime.fromisoformat(f"{date_str}T{time_str}").replace(
        tzinfo=MONTREAL_TZ
    )
    return local_dt.astimezone(UTC).isoformat()
