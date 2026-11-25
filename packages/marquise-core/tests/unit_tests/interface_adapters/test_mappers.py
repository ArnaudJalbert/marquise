"""Unit tests for shared interface adapter mappers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from marquise.interface_adapters.mappers import to_aware_utc


def test_to_aware_utc_marks_naive_as_utc_and_keeps_aware() -> None:
    """Naive database timestamps become UTC-aware; aware values keep their offset."""
    montreal_evening = datetime(
        2026, 11, 25, 19, 30, tzinfo=timezone(timedelta(hours=-5))
    )

    assert to_aware_utc(datetime(2026, 11, 26, 0, 30)) == datetime(
        2026, 11, 26, 0, 30, tzinfo=UTC
    )
    assert to_aware_utc(datetime(2026, 11, 26, 0, 30)).tzinfo is UTC
    assert to_aware_utc(montreal_evening) is montreal_evening
