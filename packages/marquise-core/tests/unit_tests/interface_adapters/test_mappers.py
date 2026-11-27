"""Unit tests for shared interface adapter mappers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from marquise.interface_adapters.mappers import to_aware_utc


def test_to_aware_utc_marks_naive_as_utc_and_shifts_aware_to_utc() -> None:
    """Naive timestamps become UTC-aware; aware values shift to the same UTC instant."""
    montreal_evening = datetime(
        2026, 11, 25, 19, 30, tzinfo=timezone(timedelta(hours=-5))
    )
    utc_instant = datetime(2026, 11, 26, 0, 30, tzinfo=UTC)

    assert to_aware_utc(datetime(2026, 11, 26, 0, 30)) == utc_instant
    assert to_aware_utc(datetime(2026, 11, 26, 0, 30)).tzinfo is UTC
    assert to_aware_utc(montreal_evening) == utc_instant
    assert to_aware_utc(montreal_evening).tzinfo is UTC
