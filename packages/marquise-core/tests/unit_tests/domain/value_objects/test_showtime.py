"""Tests for Showtime value object."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from marquise.domain.value_objects.showtime import Showtime


def test_showtime_creation() -> None:
    """Verify Showtime can be created with a datetime value."""
    st = Showtime(value=datetime(2026, 6, 6, 19, 30, 0, tzinfo=UTC))
    assert st.value == datetime(2026, 6, 6, 19, 30, 0, tzinfo=UTC)


def test_showtime_str() -> None:
    """Verify the string representation is ISO 8601."""
    st = Showtime(value=datetime(2026, 6, 6, 19, 30, 0, tzinfo=UTC))
    assert str(st) == "2026-06-06T19:30:00+00:00"


def test_showtime_hash() -> None:
    """Verify Showtime hashing is based on value equality."""
    st1 = Showtime(value=datetime(2026, 6, 6, 19, 30, 0, tzinfo=UTC))
    st2 = Showtime(value=datetime(2026, 6, 6, 19, 30, 0, tzinfo=UTC))
    assert hash(st1) == hash(st2)


def test_showtime_rejects_naive_datetime() -> None:
    """Verify Showtime rejects a naive datetime without tzinfo."""
    with pytest.raises(ValueError, match="datetime must be timezone-aware"):
        Showtime(value=datetime(2026, 6, 6, 19, 30, 0))
