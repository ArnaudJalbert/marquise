"""Tests for Showtime value object."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from marquise.domain.value_objects.showtime import Showtime


def test_showtime_creation() -> None:
    """Verify Showtime can be created with a datetime value."""
    st = Showtime(value=datetime(2026, 6, 6, 19, 30, 0, tzinfo=UTC))
    assert st.value == datetime(2026, 6, 6, 19, 30, 0, tzinfo=UTC)


def test_showtime_rejects_naive_datetime() -> None:
    """Verify Showtime rejects a naive datetime without tzinfo."""
    with pytest.raises(ValueError, match="datetime must be timezone-aware"):
        Showtime(value=datetime(2026, 6, 6, 19, 30, 0))
