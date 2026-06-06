"""Tests for DateValue value object."""

from __future__ import annotations

from datetime import datetime

from marquise.domain.value_objects import Showtime
from marquise.domain.value_objects.date_value import DateValue


def test_date_value_from_datetime() -> None:
    dt = datetime(2026, 6, 6, 12, 0, 0)
    dv = DateValue.from_datetime(dt)
    assert dv.value == dt


def test_date_value_str() -> None:
    dv = DateValue(value=datetime(2026, 6, 6, 12, 0, 0))
    assert str(dv) == "2026-06-06T12:00:00"


def test_date_value_hash() -> None:
    dv1 = DateValue(value=datetime(2026, 6, 6, 12, 0, 0))
    dv2 = DateValue(value=datetime(2026, 6, 6, 12, 0, 0))
    assert hash(dv1) == hash(dv2)


def test_showtime_inherits_from_date_value() -> None:
    showtime = Showtime(value=datetime(2026, 6, 6, 12, 0, 0))
    assert isinstance(showtime, DateValue)
