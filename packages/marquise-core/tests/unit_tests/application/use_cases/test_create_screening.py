"""Tests for CreateScreeningUseCase."""

from __future__ import annotations

from collections.abc import Callable
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


@pytest.fixture
def movie() -> Movie:
    """Provide a sample movie for create tests."""
    return Movie(id=MovieId(value="mov-1"), title="The Odyssey")


@pytest.fixture
def cinema() -> Cinema:
    """Provide a sample cinema for create tests."""
    return Cinema(id=CinemaId(value="cin-1"), name="Cinema One")


@pytest.fixture
def screening(movie: Movie, cinema: Cinema) -> Screening:
    """Provide a persisted screening returned by save."""
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=movie,
        cinema=cinema,
        showtime=Showtime(value=SHOWTIME),
        ticket_url="https://tickets.example/1",
        room="Salle 4",
        language="V.O.",
    )


@pytest.fixture
def screening_repository(screening: Screening) -> ScreeningRepository:
    """Provide an autospecced screening repository with a successful save."""
    repository = create_autospec(ScreeningRepository, instance=True)
    repository.save.return_value = screening
    return repository


@pytest.fixture
def movie_repository(movie: Movie) -> MovieRepository:
    """Provide an autospecced movie repository that finds the sample movie."""
    repository = create_autospec(MovieRepository, instance=True)
    repository.find_by_id.return_value = movie
    return repository


@pytest.fixture
def cinema_repository(cinema: Cinema) -> CinemaRepository:
    """Provide an autospecced cinema repository that finds the sample cinema."""
    repository = create_autospec(CinemaRepository, instance=True)
    repository.find_by_id.return_value = cinema
    return repository


@pytest.fixture
def use_case(
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
    cinema_repository: CinemaRepository,
) -> CreateScreeningUseCase:
    """Provide a configured create-screening use case."""
    return CreateScreeningUseCase(
        screening_repository=screening_repository,
        movie_repository=movie_repository,
        cinema_repository=cinema_repository,
    )


@pytest.fixture
def create_input() -> Callable[..., CreateScreeningUseCase.InputData]:
    """Build create input data with optional field overrides."""

    def _create_input(**overrides: object) -> CreateScreeningUseCase.InputData:
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

    return _create_input


@pytest.mark.asyncio
async def test_creates_screening_and_returns_output(
    use_case: CreateScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
    cinema_repository: CinemaRepository,
    create_input: Callable[..., CreateScreeningUseCase.InputData],
) -> None:
    """A valid create looks up parents, saves, and returns output data."""
    result = await use_case.execute(create_input())

    assert result.id == "scr-1"
    assert result.movie_id == "mov-1"
    assert result.movie_title == "The Odyssey"
    assert result.cinema_id == "cin-1"
    assert result.cinema_name == "Cinema One"
    assert result.showtime == SHOWTIME
    assert result.ticket_url == "https://tickets.example/1"
    assert result.room == "Salle 4"
    assert result.language == "V.O."
    movie_repository.find_by_id.assert_awaited_once_with(MovieId(value="mov-1"))
    cinema_repository.find_by_id.assert_awaited_once_with(CinemaId(value="cin-1"))
    screening_repository.save.assert_awaited_once()
    saved = screening_repository.save.await_args.args[0]
    assert saved.movie.id == MovieId(value="mov-1")
    assert saved.cinema.id == CinemaId(value="cin-1")
    assert saved.showtime.value == SHOWTIME


@pytest.mark.asyncio
async def test_raises_when_movie_missing(
    use_case: CreateScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
    create_input: Callable[..., CreateScreeningUseCase.InputData],
) -> None:
    """Unknown movie IDs are rejected before save."""
    movie_repository.find_by_id.return_value = None

    with pytest.raises(MovieNotFoundError, match="mov-1"):
        await use_case.execute(create_input())

    screening_repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_cinema_missing(
    use_case: CreateScreeningUseCase,
    screening_repository: ScreeningRepository,
    cinema_repository: CinemaRepository,
    create_input: Callable[..., CreateScreeningUseCase.InputData],
) -> None:
    """Unknown cinema IDs are rejected before save."""
    cinema_repository.find_by_id.return_value = None

    with pytest.raises(CinemaNotFoundError, match="cin-1"):
        await use_case.execute(create_input())

    screening_repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_screening_already_exists(
    use_case: CreateScreeningUseCase,
    screening_repository: ScreeningRepository,
    create_input: Callable[..., CreateScreeningUseCase.InputData],
) -> None:
    """A duplicate screening surfaces ScreeningAlreadyExistsError."""
    screening_repository.save.side_effect = ScreeningAlreadyExistsError(
        "already exists"
    )

    with pytest.raises(ScreeningAlreadyExistsError, match="already exists"):
        await use_case.execute(create_input())


def test_input_rejects_empty_ids(
    create_input: Callable[..., CreateScreeningUseCase.InputData],
) -> None:
    """Empty movie_id or cinema_id is rejected."""
    with pytest.raises(ValueError, match="movie_id must not be empty"):
        create_input(movie_id="  ")
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        create_input(cinema_id="")


def test_input_rejects_naive_showtime(
    create_input: Callable[..., CreateScreeningUseCase.InputData],
) -> None:
    """Naive showtimes are rejected at the use-case boundary."""
    with pytest.raises(ValueError, match="showtime must be timezone-aware"):
        create_input(showtime=datetime(2026, 6, 27, 19, 30))


def test_input_rejects_blank_optionals_when_provided(
    create_input: Callable[..., CreateScreeningUseCase.InputData],
) -> None:
    """Provided optional strings must not be whitespace-only."""
    with pytest.raises(ValueError, match="ticket_url must not be empty when provided"):
        create_input(ticket_url="  ")
    with pytest.raises(ValueError, match="room must not be empty when provided"):
        create_input(room="")
    with pytest.raises(ValueError, match="language must not be empty when provided"):
        create_input(language=" ")
    with pytest.raises(ValueError, match="external_id must not be empty when provided"):
        create_input(external_id="")
