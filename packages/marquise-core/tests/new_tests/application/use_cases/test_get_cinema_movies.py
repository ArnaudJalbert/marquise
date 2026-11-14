"""Input contract for the cinema movies date range."""

from datetime import UTC, datetime

import pytest

from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase


def test_input_rejects_naive_start_date() -> None:
    """A start date without a timezone fails before the use case runs."""
    with pytest.raises(ValueError, match="start_date must be timezone-aware"):
        GetCinemaMoviesUseCase.InputData(
            cinema_id="cin-1",
            start_date=datetime(2026, 6, 27),
            end_date=datetime(2026, 6, 28, tzinfo=UTC),
        )


def test_input_rejects_naive_end_date() -> None:
    """An end date without a timezone fails before the use case runs."""
    with pytest.raises(ValueError, match="end_date must be timezone-aware"):
        GetCinemaMoviesUseCase.InputData(
            cinema_id="cin-1",
            start_date=datetime(2026, 6, 27, tzinfo=UTC),
            end_date=datetime(2026, 6, 28),
        )
