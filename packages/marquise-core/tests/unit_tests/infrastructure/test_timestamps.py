"""Unit tests for PostgreSQL timestamp conversion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from marquise.infrastructure.postgres.timestamps import to_naive_utc


def test_to_naive_utc_converts_aware_offset_and_keeps_naive() -> None:
    """Aware values shift to UTC and drop tzinfo; naive values already hold UTC."""
    montreal_evening = datetime(
        2026, 11, 25, 19, 30, tzinfo=timezone(timedelta(hours=-5))
    )
    naive_utc = datetime(2026, 11, 26, 0, 30)

    assert to_naive_utc(montreal_evening) == naive_utc
    assert to_naive_utc(montreal_evening).tzinfo is None
    assert to_naive_utc(naive_utc) == naive_utc
