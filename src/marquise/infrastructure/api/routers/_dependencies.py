"""Shared FastAPI query-parameter dependencies for the read-only routers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Query


def _start_of_today_utc() -> datetime:
    """Return the current UTC date at midnight, timezone-aware.

    Returns:
        A timezone-aware ``datetime`` for today's date at 00:00 UTC.
    """
    now = datetime.now(UTC)
    return datetime(now.year, now.month, now.day, tzinfo=UTC)


def resolve_showtimes_date_range(
    from_: datetime | None = Query(
        default=None,
        alias="from",
        description="Start of range (inclusive). Defaults to the start of today (UTC).",
    ),
    to: datetime | None = Query(
        default=None,
        description="End of range (inclusive). Defaults to one week from start.",
    ),
) -> tuple[datetime, datetime]:
    """Resolve the effective showtimes date range, applying defaults.

    Defaults are resolved here, as a dependency, rather than inside the
    cached endpoint body: fastapi-cache2 builds its cache key from the
    arguments FastAPI already resolved before the endpoint runs, so if
    ``from``/``to`` stayed ``None`` until the function body ran, every
    request that omits them would collide on one cache entry frozen at
    whichever moment first populated it.

    Returns:
        A ``(start, end)`` tuple, both timezone-aware.
    """
    resolved_from = from_ if from_ is not None else _start_of_today_utc()
    resolved_to = to if to is not None else resolved_from + timedelta(days=7)
    return resolved_from, resolved_to
