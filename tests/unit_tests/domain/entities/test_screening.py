"""Tests for Screening entity."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.exceptions import ScreeningError
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    Price,
    ScreeningId,
    Showtime,
)


@pytest.fixture
def sample_cinema() -> Cinema:
    return Cinema(id=CinemaId(value="cin-123"), name="Test Cinema", city="Montreal")


@pytest.fixture
def sample_movie() -> Movie:
    return Movie(
        id=MovieId(value="mov-123"),
        title="Inception",
        release_date=datetime.now().date(),
        directors=("Christopher Nolan",),
        cast=("Actor",),
    )


@pytest.fixture
def sample_showtime() -> Showtime:
    return Showtime(value=datetime.utcnow() + timedelta(days=1))


@pytest.fixture
def sample_price() -> Price:
    return Price(value=14.99)


def create_screening(
    showtime: Showtime,
    cinema: Cinema,
    movie: Movie,
    price: Price,
) -> Screening:
    return Screening(
        id=ScreeningId(value="scr-123"),
        movie_id=movie,
        cinema_id=cinema,
        showtime=showtime,
        price=price,
    )


def test_screening_creation(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    screening = create_screening(
        sample_showtime, sample_cinema, sample_movie, sample_price
    )
    assert screening.id == ScreeningId(value="scr-123")
    assert screening.movie_id == sample_movie
    assert screening.cinema_id == sample_cinema
    assert screening.showtime == sample_showtime
    assert screening.price == sample_price
    assert screening.available_seats is None
    assert screening.is_sold_out is None


def test_screening_rejects_negative_available_seats(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    screening = create_screening(
        sample_showtime, sample_cinema, sample_movie, sample_price
    )
    screening.available_seats = -1
    with pytest.raises(ScreeningError, match="Available seats cannot be negative"):
        screening.__post_init__()


def test_screening_rejects_negative_price(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
) -> None:
    with pytest.raises(ScreeningError, match="Price cannot be negative"):
        Screening(
            id=ScreeningId(value="scr-123"),
            movie_id=sample_movie,
            cinema_id=sample_cinema,
            showtime=sample_showtime,
            price=Price(value=-5.0),
        )


def test_is_upcoming_returns_true_when_showtime_is_future(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_price: Price,
) -> None:
    future = Showtime(value=datetime.utcnow() + timedelta(hours=1))
    screening = create_screening(future, sample_cinema, sample_movie, sample_price)
    assert screening.is_upcoming()


def test_is_upcoming_returns_false_when_showtime_is_past(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_price: Price,
) -> None:
    past = Showtime(value=datetime.utcnow() - timedelta(hours=1))
    screening = create_screening(past, sample_cinema, sample_movie, sample_price)
    assert not screening.is_upcoming()


def test_is_upcoming_with_explicit_now(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_price: Price,
) -> None:
    showtime = Showtime(value=datetime(2026, 6, 6, 12, 0, 0))
    screening = create_screening(showtime, sample_cinema, sample_movie, sample_price)
    assert screening.is_upcoming(now=datetime(2026, 6, 6, 11, 0, 0))
    assert not screening.is_upcoming(now=datetime(2026, 6, 6, 13, 0, 0))


def test_has_ended_returns_true_when_showtime_is_past(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_price: Price,
) -> None:
    past = Showtime(value=datetime.utcnow() - timedelta(hours=1))
    screening = create_screening(past, sample_cinema, sample_movie, sample_price)
    assert screening.has_ended()


def test_has_ended_returns_false_when_showtime_is_future(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_price: Price,
) -> None:
    future = Showtime(value=datetime.utcnow() + timedelta(hours=1))
    screening = create_screening(future, sample_cinema, sample_movie, sample_price)
    assert not screening.has_ended()


def test_has_ended_with_explicit_now(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_price: Price,
) -> None:
    showtime = Showtime(value=datetime(2026, 6, 6, 12, 0, 0))
    screening = create_screening(showtime, sample_cinema, sample_movie, sample_price)
    assert screening.has_ended(now=datetime(2026, 6, 6, 13, 0, 0))
    assert not screening.has_ended(now=datetime(2026, 6, 6, 11, 0, 0))


def test_update_availability_raises_error_when_seats_unknown(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    screening = create_screening(
        sample_showtime, sample_cinema, sample_movie, sample_price
    )
    with pytest.raises(
        ScreeningError, match="Cannot update availability: seats unknown"
    ):
        screening.update_availability(seats_sold=5)


def test_update_availability_raises_error_when_seats_sold_negative(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    screening = create_screening(
        sample_showtime, sample_cinema, sample_movie, sample_price
    )
    screening.available_seats = 10
    with pytest.raises(ScreeningError, match="Seats sold cannot be negative"):
        screening.update_availability(seats_sold=-1)


def test_update_availability_raises_error_when_overselling(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    screening = create_screening(
        sample_showtime, sample_cinema, sample_movie, sample_price
    )
    screening.available_seats = 5
    with pytest.raises(ScreeningError, match="Cannot sell more seats than available"):
        screening.update_availability(seats_sold=10)


def test_update_availability_decreases_seats(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    screening = create_screening(
        sample_showtime, sample_cinema, sample_movie, sample_price
    )
    screening.available_seats = 10
    screening.update_availability(seats_sold=3)
    assert screening.available_seats == 7
    assert screening.is_sold_out is False


def test_update_availability_marks_sold_out(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    screening = create_screening(
        sample_showtime, sample_cinema, sample_movie, sample_price
    )
    screening.available_seats = 5
    screening.update_availability(seats_sold=5)
    assert screening.available_seats == 0
    assert screening.is_sold_out is True


def test_screening_str_representation(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
    sample_price: Price,
) -> None:
    screening = create_screening(
        sample_showtime, sample_cinema, sample_movie, sample_price
    )
    result = str(screening)
    assert str(sample_movie) in result
    assert str(sample_cinema) in result
    assert str(sample_showtime) in result
