"""Tests for DateValue value object."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from marquise.domain.value_objects import Showtime
from marquise.domain.value_objects.date_value import DateValue


def test_date_value_from_datetime() -> None:
    """Verify DateValue can be created via the from_datetime classmethod."""
    dt = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
    dv = DateValue.from_datetime(dt)
    assert dv.value == dt


def test_date_value_str() -> None:
    """Verify the string representation is ISO 8601."""
    dv = DateValue(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC))
    assert str(dv) == "2026-06-06T12:00:00+00:00"


def test_date_value_hash() -> None:
    """Verify DateValue hashing is based on value equality."""
    dv1 = DateValue(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC))
    dv2 = DateValue(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC))
    assert hash(dv1) == hash(dv2)


def test_showtime_inherits_from_date_value() -> None:
    """Verify Showtime is a subclass of DateValue."""
    showtime = Showtime(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC))
    assert isinstance(showtime, DateValue)


def test_date_value_rejects_naive_datetime() -> None:
    """Verify DateValue rejects a naive datetime without tzinfo."""
    with pytest.raises(ValueError, match="datetime must be timezone-aware"):
        DateValue(value=datetime(2026, 6, 6, 12, 0, 0))
