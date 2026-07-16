"""Tests for the shared Montreal-local to UTC conversion helper."""

from __future__ import annotations

from marquise.infrastructure.sources._timezone import montreal_local_to_utc_iso


def test_montreal_local_to_utc_iso_converts_summer_time_edt() -> None:
    """A summer showtime is EDT (UTC-4)."""
    result = montreal_local_to_utc_iso("2026-07-13", "17:00")
    assert result == "2026-07-13T21:00:00+00:00"


def test_montreal_local_to_utc_iso_converts_winter_time_est() -> None:
    """A winter showtime is EST (UTC-5)."""
    result = montreal_local_to_utc_iso("2026-01-13", "17:00")
    assert result == "2026-01-13T22:00:00+00:00"


def test_montreal_local_to_utc_iso_crosses_midnight_utc() -> None:
    """A late Eastern showtime rolls over to the next UTC calendar day."""
    result = montreal_local_to_utc_iso("2026-07-13", "22:00")
    assert result == "2026-07-14T02:00:00+00:00"
