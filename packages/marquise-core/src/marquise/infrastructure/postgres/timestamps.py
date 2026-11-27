"""Timestamp conversion for PostgreSQL ``TIMESTAMP`` columns holding UTC."""

from __future__ import annotations

from datetime import UTC, datetime


def to_naive_utc(value: datetime) -> datetime:
    """Convert a datetime to the naive UTC form stored in PostgreSQL.

    Args:
        value: An aware datetime, or a naive one already in UTC.

    Returns:
        A naive datetime in UTC.
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
