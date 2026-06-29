"""Tests for ShowtimeRow boundary validation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from marquise.application.repositories.source_registry_query import ShowtimeRow


def test_showtime_row_accepts_valid_row() -> None:
    """A row with a non-empty title and tz-aware showtime is accepted."""
    row = ShowtimeRow(
        movie_title="The Odyssey",
        showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
    )
    assert row.movie_title == "The Odyssey"
    assert row.showtime.tzinfo is not None


def test_showtime_row_rejects_empty_title() -> None:
    """An empty movie title is rejected."""
    with pytest.raises(ValueError, match="movie_title must not be empty"):
        ShowtimeRow(
            movie_title="",
            showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
        )


def test_showtime_row_rejects_whitespace_title() -> None:
    """A whitespace-only movie title is rejected."""
    with pytest.raises(ValueError, match="movie_title must not be empty"):
        ShowtimeRow(
            movie_title="   ",
            showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
        )


def test_showtime_row_rejects_naive_datetime() -> None:
    """A naive (timezone-unaware) showtime is rejected."""
    with pytest.raises(ValueError, match="showtime must be timezone-aware"):
        ShowtimeRow(
            movie_title="The Odyssey",
            showtime=datetime(2026, 6, 27, 19, 30),
        )
