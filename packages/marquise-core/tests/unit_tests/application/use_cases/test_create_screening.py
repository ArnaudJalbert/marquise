"""Tests for CreateScreeningUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    MovieNotFoundError,
    ScreeningAlreadyExistsError,
)
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
)
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime

SHOWTIME = datetime(2026, 6, 27, 19, 30, tzinfo=UTC)


def _movie() -> Movie:
    return Movie(id=MovieId(value="mov-1"), title="The Odyssey")


def _cinema() -> Cinema:
    return Cinema(id=CinemaId(value="cin-1"), name="Cinema One")


def _screening() -> Screening:
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=_movie(),
        cinema=_cinema(),
        showtime=Showtime(value=SHOWTIME),
        ticket_url="https://tickets.example/1",
        room="Salle 4",
        language="V.O.",
    )


def _input(**overrides: object) -> CreateScreeningUseCase.InputData:
    values: dict[str, object] = {
        "movie_id": "mov-1",
        "cinema_id": "cin-1",
        "showtime": SHOWTIME,
        "ticket_url": "https://tickets.example/1",
        "room": "Salle 4",
        "language": "V.O.",
    }
    values.update(overrides)
    return CreateScreeningUseCase.InputData(**values)  # type: ignore[arg-type]


def _use_case() -> tuple[
    CreateScreeningUseCase,
    ScreeningRepository,
    MovieRepository,
    CinemaRepository,
]:
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    movie_repo = create_autospec(MovieRepository, instance=True)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    movie_repo.find_by_id.return_value = _movie()
    cinema_repo.find_by_id.return_value = _cinema()
    screening_repo.save.return_value = _screening()
    return (
        CreateScreeningUseCase(
            screening_repository=screening_repo,
            movie_repository=movie_repo,
            cinema_repository=cinema_repo,
        ),
        screening_repo,
        movie_repo,
        cinema_repo,
    )


@pytest.mark.asyncio
async def test_creates_screening_and_returns_output() -> None:
    """A valid create looks up parents, saves, and returns output data."""
    use_case, screening_repo, movie_repo, cinema_repo = _use_case()

    result = await use_case.execute(_input())

    assert result.id == "scr-1"
    assert result.movie_id == "mov-1"
    assert result.movie_title == "The Odyssey"
    assert result.cinema_id == "cin-1"
    assert result.cinema_name == "Cinema One"
    assert result.showtime == SHOWTIME
    assert result.ticket_url == "https://tickets.example/1"
    assert result.room == "Salle 4"
    assert result.language == "V.O."
    movie_repo.find_by_id.assert_awaited_once_with(MovieId(value="mov-1"))
    cinema_repo.find_by_id.assert_awaited_once_with(CinemaId(value="cin-1"))
    screening_repo.save.assert_awaited_once()
    saved = screening_repo.save.await_args.args[0]
    assert saved.movie.id == MovieId(value="mov-1")
    assert saved.cinema.id == CinemaId(value="cin-1")
    assert saved.showtime.value == SHOWTIME


@pytest.mark.asyncio
async def test_raises_when_movie_missing() -> None:
    """Unknown movie IDs are rejected before save."""
    use_case, screening_repo, movie_repo, _cinema_repo = _use_case()
    movie_repo.find_by_id.return_value = None

    with pytest.raises(MovieNotFoundError, match="mov-1"):
        await use_case.execute(_input())

    screening_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_cinema_missing() -> None:
    """Unknown cinema IDs are rejected before save."""
    use_case, screening_repo, _movie_repo, cinema_repo = _use_case()
    cinema_repo.find_by_id.return_value = None

    with pytest.raises(CinemaNotFoundError, match="cin-1"):
        await use_case.execute(_input())

    screening_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_screening_already_exists() -> None:
    """A duplicate screening surfaces ScreeningAlreadyExistsError."""
    use_case, screening_repo, _movie_repo, _cinema_repo = _use_case()
    screening_repo.save.side_effect = ScreeningAlreadyExistsError("already exists")

    with pytest.raises(ScreeningAlreadyExistsError, match="already exists"):
        await use_case.execute(_input())


def test_input_rejects_empty_ids() -> None:
    """Empty movie_id or cinema_id is rejected."""
    with pytest.raises(ValueError, match="movie_id must not be empty"):
        _input(movie_id="  ")
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        _input(cinema_id="")


def test_input_rejects_naive_showtime() -> None:
    """Naive showtimes are rejected at the use-case boundary."""
    with pytest.raises(ValueError, match="showtime must be timezone-aware"):
        _input(showtime=datetime(2026, 6, 27, 19, 30))


def test_input_rejects_blank_optionals_when_provided() -> None:
    """Provided optional strings must not be whitespace-only."""
    with pytest.raises(ValueError, match="ticket_url must not be empty when provided"):
        _input(ticket_url="  ")
    with pytest.raises(ValueError, match="room must not be empty when provided"):
        _input(room="")
    with pytest.raises(ValueError, match="language must not be empty when provided"):
        _input(language=" ")
    with pytest.raises(ValueError, match="external_id must not be empty when provided"):
        _input(external_id="")
