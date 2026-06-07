"""Tests for ReleaseDate value object."""

from __future__ import annotations

from datetime import datetime, timezone

from marquise.domain.value_objects.release_date import ReleaseDate


def test_release_date_creation() -> None:
    """Verify ReleaseDate can be created with a datetime value."""
    rd = ReleaseDate(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc))
    assert rd.value == datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)


def test_release_date_str() -> None:
    """Verify the string representation is ISO 8601."""
    rd = ReleaseDate(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc))
    assert str(rd) == "2026-06-06T12:00:00+00:00"


def test_release_date_hash() -> None:
    """Verify ReleaseDate hashing is based on value equality."""
    rd1 = ReleaseDate(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc))
    rd2 = ReleaseDate(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc))
    assert hash(rd1) == hash(rd2)
