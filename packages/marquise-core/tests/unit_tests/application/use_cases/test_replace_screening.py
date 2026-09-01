"""Tests for ReplaceScreeningUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    MovieNotFoundError,
    ScreeningAlreadyExistsError,
    ScreeningNotFoundError,
)
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
)
from marquise.application.use_cases.replace_screening import ReplaceScreeningUseCase
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime

OLD_SHOWTIME = datetime(2026, 6, 27, 19, 30, tzinfo=UTC)
NEW_SHOWTIME = datetime(2026, 6, 28, 21, 0, tzinfo=UTC)


def _existing() -> Screening:
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=Movie(id=MovieId(value="mov-1"), title="The Odyssey"),
        cinema=Cinema(id=CinemaId(value="cin-1"), name="Cinema One"),
        showtime=Showtime(value=OLD_SHOWTIME),
        ticket_url="https://old.example/t",
        room="Salle 1",
        language="V.F.",
    )


def _replacement_movie() -> Movie:
    return Movie(id=MovieId(value="mov-2"), title="Dune")


def _replacement_cinema() -> Cinema:
    return Cinema(id=CinemaId(value="cin-2"), name="Cinema Two")


def _replaced() -> Screening:
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=_replacement_movie(),
        cinema=_replacement_cinema(),
        showtime=Showtime(value=NEW_SHOWTIME),
        ticket_url=None,
        room="Salle 9",
        language="V.O.",
    )


def _input(**overrides: object) -> ReplaceScreeningUseCase.InputData:
    values: dict[str, object] = {
        "screening_id": "scr-1",
        "movie_id": "mov-2",
        "cinema_id": "cin-2",
        "showtime": NEW_SHOWTIME,
        "ticket_url": None,
        "room": "Salle 9",
        "language": "V.O.",
    }
    values.update(overrides)
    return ReplaceScreeningUseCase.InputData(**values)  # type: ignore[arg-type]


def _use_case() -> tuple[
    ReplaceScreeningUseCase,
    ScreeningRepository,
    MovieRepository,
    CinemaRepository,
]:
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    movie_repo = create_autospec(MovieRepository, instance=True)
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    screening_repo.find_by_id.return_value = _existing()
    movie_repo.find_by_id.return_value = _replacement_movie()
    cinema_repo.find_by_id.return_value = _replacement_cinema()
    screening_repo.replace.return_value = _replaced()
    return (
        ReplaceScreeningUseCase(
            screening_repository=screening_repo,
            movie_repository=movie_repo,
            cinema_repository=cinema_repo,
        ),
        screening_repo,
        movie_repo,
        cinema_repo,
    )


@pytest.mark.asyncio
async def test_replaces_all_fields_including_identity() -> None:
    """PUT replaces identity and optional fields, keeping the screening ID."""
    use_case, screening_repo, movie_repo, cinema_repo = _use_case()

    result = await use_case.execute(_input())

    assert result.id == "scr-1"
    assert result.movie_id == "mov-2"
    assert result.movie_title == "Dune"
    assert result.cinema_id == "cin-2"
    assert result.cinema_name == "Cinema Two"
    assert result.showtime == NEW_SHOWTIME
    assert result.ticket_url is None
    assert result.room == "Salle 9"
    assert result.language == "V.O."
    screening_repo.find_by_id.assert_awaited_once_with(ScreeningId(value="scr-1"))
    movie_repo.find_by_id.assert_awaited_once_with(MovieId(value="mov-2"))
    cinema_repo.find_by_id.assert_awaited_once_with(CinemaId(value="cin-2"))
    screening_repo.replace.assert_awaited_once()
    submitted = screening_repo.replace.await_args.args[0]
    assert submitted.id == ScreeningId(value="scr-1")
    assert submitted.movie.id == MovieId(value="mov-2")
    assert submitted.cinema.id == CinemaId(value="cin-2")
    assert submitted.showtime.value == NEW_SHOWTIME
    assert submitted.ticket_url is None


@pytest.mark.asyncio
async def test_reuses_existing_parents_when_identity_unchanged() -> None:
    """Unchanged movie and cinema IDs do not trigger extra lookups."""
    use_case, screening_repo, movie_repo, cinema_repo = _use_case()
    screening_repo.replace.return_value = _existing()

    await use_case.execute(_input(movie_id="mov-1", cinema_id="cin-1"))

    movie_repo.find_by_id.assert_not_awaited()
    cinema_repo.find_by_id.assert_not_awaited()
    submitted = screening_repo.replace.await_args.args[0]
    assert submitted.movie.title == "The Odyssey"
    assert submitted.cinema.name == "Cinema One"


@pytest.mark.asyncio
async def test_raises_when_screening_missing() -> None:
    """PUT of an unknown screening raises ScreeningNotFoundError."""
    use_case, screening_repo, movie_repo, cinema_repo = _use_case()
    screening_repo.find_by_id.side_effect = ScreeningNotFoundError(
        "A screening with ID 'missing' was not found"
    )

    with pytest.raises(ScreeningNotFoundError, match="missing"):
        await use_case.execute(_input(screening_id="missing"))

    movie_repo.find_by_id.assert_not_awaited()
    cinema_repo.find_by_id.assert_not_awaited()
    screening_repo.replace.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_movie_missing() -> None:
    """Unknown replacement movie IDs are rejected before persist."""
    use_case, screening_repo, movie_repo, _cinema_repo = _use_case()
    movie_repo.find_by_id.return_value = None

    with pytest.raises(MovieNotFoundError, match="mov-2"):
        await use_case.execute(_input())

    screening_repo.replace.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_cinema_missing() -> None:
    """Unknown replacement cinema IDs are rejected before persist."""
    use_case, screening_repo, _movie_repo, cinema_repo = _use_case()
    cinema_repo.find_by_id.return_value = None

    with pytest.raises(CinemaNotFoundError, match="cin-2"):
        await use_case.execute(_input())

    screening_repo.replace.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_replacement_conflicts() -> None:
    """A unique-constraint conflict surfaces ScreeningAlreadyExistsError."""
    use_case, screening_repo, _movie_repo, _cinema_repo = _use_case()
    screening_repo.replace.side_effect = ScreeningAlreadyExistsError("already exists")

    with pytest.raises(ScreeningAlreadyExistsError, match="already exists"):
        await use_case.execute(_input())


def test_input_rejects_empty_ids() -> None:
    """Empty identity fields are rejected."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        _input(screening_id=" ")
    with pytest.raises(ValueError, match="movie_id must not be empty"):
        _input(movie_id="")
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        _input(cinema_id="  ")


def test_input_rejects_naive_showtime() -> None:
    """Naive showtimes are rejected at the use-case boundary."""
    with pytest.raises(ValueError, match="showtime must be timezone-aware"):
        _input(showtime=datetime(2026, 6, 28, 21, 0))


def test_input_rejects_blank_optionals_when_provided() -> None:
    """Provided optional strings must not be whitespace-only."""
    with pytest.raises(ValueError, match="ticket_url must not be empty when provided"):
        _input(ticket_url=" ")
    with pytest.raises(ValueError, match="room must not be empty when provided"):
        _input(room="")
    with pytest.raises(ValueError, match="language must not be empty when provided"):
        _input(language="  ")
    with pytest.raises(ValueError, match="external_id must not be empty when provided"):
        _input(external_id="")
