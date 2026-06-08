"""Tests for Screening entity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from marquise.domain.entities import Screening
from marquise.domain.exceptions import ScreeningError
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    Price,
    ScreeningId,
    Showtime,
)


@pytest.fixture
def sample_cinema_id() -> CinemaId:
    """Provide a sample CinemaId for tests."""
    return CinemaId(value="cin-123")


@pytest.fixture
def sample_movie_id() -> MovieId:
    """Provide a sample MovieId for tests."""
    return MovieId(value="mov-123")


@pytest.fixture
def sample_showtime() -> Showtime:
    """Provide a future Showtime for tests."""
    return Showtime(value=datetime.now(timezone.utc) + timedelta(days=1))


@pytest.fixture
def sample_price() -> Price:
    """Provide a sample Price for tests."""
    return Price(value=14.99)


def create_screening(
    showtime: Showtime,
    cinema_id: CinemaId,
    movie_id: MovieId,
    price: Price,
) -> Screening:
    """Helper to build a Screening with a fixed ID."""
    return Screening(
        id=ScreeningId(value="scr-123"),
        movie_id=movie_id,
        cinema_id=cinema_id,
        showtime=showtime,
        price=price,
    )


def test_screening_creation(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    """Verify that a Screening can be created with all fields."""
    screening = create_screening(
        sample_showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    assert screening.id == ScreeningId(value="scr-123")
    assert screening.movie_id == sample_movie_id
    assert screening.cinema_id == sample_cinema_id
    assert screening.showtime == sample_showtime
    assert screening.price == sample_price
    assert screening.available_seats is None
    assert screening.is_sold_out is None


def test_screening_rejects_negative_price(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_showtime: Showtime,
) -> None:
    """Verify that a negative price raises ValueError."""
    with pytest.raises(ValueError, match="Price cannot be negative"):
        Screening(
            id=ScreeningId(value="scr-123"),
            movie_id=sample_movie_id,
            cinema_id=sample_cinema_id,
            showtime=sample_showtime,
            price=Price(value=-5.0),
        )


def test_is_upcoming_returns_true_when_showtime_is_future(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_price: Price,
) -> None:
    """Verify is_upcoming returns True for a future showtime."""
    future = Showtime(value=datetime.now(timezone.utc) + timedelta(hours=1))
    screening = create_screening(
        future, sample_cinema_id, sample_movie_id, sample_price
    )
    assert screening.is_upcoming()


def test_is_upcoming_returns_false_when_showtime_is_past(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_price: Price,
) -> None:
    """Verify is_upcoming returns False for a past showtime."""
    past = Showtime(value=datetime.now(timezone.utc) - timedelta(hours=1))
    screening = create_screening(past, sample_cinema_id, sample_movie_id, sample_price)
    assert not screening.is_upcoming()


def test_is_upcoming_with_explicit_now(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_price: Price,
) -> None:
    """Verify is_upcoming respects an explicit ``now`` parameter."""
    showtime = Showtime(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc))
    screening = create_screening(
        showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    assert screening.is_upcoming(
        now=datetime(2026, 6, 6, 11, 0, 0, tzinfo=timezone.utc)
    )
    assert not screening.is_upcoming(
        now=datetime(2026, 6, 6, 13, 0, 0, tzinfo=timezone.utc)
    )


def test_has_ended_returns_true_when_showtime_is_past(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_price: Price,
) -> None:
    """Verify has_ended returns True for a past showtime."""
    past = Showtime(value=datetime.now(timezone.utc) - timedelta(hours=1))
    screening = create_screening(past, sample_cinema_id, sample_movie_id, sample_price)
    assert screening.has_ended()


def test_has_ended_returns_false_when_showtime_is_future(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_price: Price,
) -> None:
    """Verify has_ended returns False for a future showtime."""
    future = Showtime(value=datetime.now(timezone.utc) + timedelta(hours=1))
    screening = create_screening(
        future, sample_cinema_id, sample_movie_id, sample_price
    )
    assert not screening.has_ended()


def test_has_ended_with_explicit_now(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_price: Price,
) -> None:
    """Verify has_ended respects an explicit ``now`` parameter."""
    showtime = Showtime(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc))
    screening = create_screening(
        showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    assert screening.has_ended(now=datetime(2026, 6, 6, 13, 0, 0, tzinfo=timezone.utc))
    assert not screening.has_ended(
        now=datetime(2026, 6, 6, 11, 0, 0, tzinfo=timezone.utc)
    )


def test_update_availability_raises_error_when_seats_unknown(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    """Verify update_availability fails when available_seats is None."""
    screening = create_screening(
        sample_showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    with pytest.raises(
        ScreeningError, match="Cannot update availability: seats unknown"
    ):
        screening.update_availability(seats_sold=5)


def test_update_availability_raises_error_when_seats_sold_negative(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    """Verify update_availability rejects negative seats_sold."""
    screening = create_screening(
        sample_showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    screening.available_seats = 10
    with pytest.raises(ScreeningError, match="Seats sold cannot be negative"):
        screening.update_availability(seats_sold=-1)


def test_update_availability_raises_error_when_overselling(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    """Verify update_availability prevents selling more seats than available."""
    screening = create_screening(
        sample_showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    screening.available_seats = 5
    with pytest.raises(ScreeningError, match="Cannot sell more seats than available"):
        screening.update_availability(seats_sold=10)


def test_update_availability_decreases_seats(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    """Verify update_availability correctly decrements available seats."""
    screening = create_screening(
        sample_showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    screening.available_seats = 10
    screening.update_availability(seats_sold=3)
    assert screening.available_seats == 7
    assert screening.is_sold_out is False


def test_update_availability_marks_sold_out(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    """Verify update_availability sets is_sold_out when seats reach zero."""
    screening = create_screening(
        sample_showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    screening.available_seats = 5
    screening.update_availability(seats_sold=5)
    assert screening.available_seats == 0
    assert screening.is_sold_out is True


def test_screening_str_representation(
    sample_cinema_id: CinemaId,
    sample_movie_id: MovieId,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    """Verify the string representation includes movie_id, cinema_id, and showtime."""
    screening = create_screening(
        sample_showtime, sample_cinema_id, sample_movie_id, sample_price
    )
    result = str(screening)
    assert str(sample_movie_id) in result
    assert str(sample_cinema_id) in result
    assert str(sample_showtime) in result
