"""Tests for CreateScreeningsCommand."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningAlreadyExistsError
from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases.create_screenings import (
    CreateScreeningsCommand,
)
from marquise.domain.value_objects import MovieId


def _make_screening_input(
    movie_id: str = "mov-a",
    movie_title: str = "Movie A",
    cinema_id: str = "cin-123",
    cinema_name: str = "Cinéma Beaubien",
    showtime: datetime | None = None,
    external_id: str | None = None,
) -> CreateScreeningsCommand.ScreeningInput:
    return CreateScreeningsCommand.ScreeningInput(
        movie_id=movie_id,
        movie_title=movie_title,
        cinema_id=cinema_id,
        cinema_name=cinema_name,
        showtime=showtime or datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        external_id=external_id,
        ticket_url=None,
        room=None,
        language=None,
    )


async def _run(
    command: CreateScreeningsCommand,
    screenings: tuple[CreateScreeningsCommand.ScreeningInput, ...],
) -> CreateScreeningsCommand.OutputData:
    return await command.execute(
        CreateScreeningsCommand.InputData(screenings=screenings)
    )


@pytest.mark.asyncio
async def test_creates_new_screenings() -> None:
    """Test that new screenings are created and counted as imported."""
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.return_value = None

    rows = (
        _make_screening_input(
            movie_id="mov-a",
            movie_title="Movie A",
            showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        ),
        _make_screening_input(
            movie_id="mov-b",
            movie_title="Movie B",
            showtime=datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC),
        ),
    )

    result = await _run(
        CreateScreeningsCommand(screening_repository=mock_screening_repo),
        rows,
    )

    assert result.total_count == 2
    assert result.imported_count == 2
    assert result.updated_count == 0
    assert result.skipped_count == 0
    assert result.screenings[0].imported is True
    assert result.screenings[1].imported is True
    assert mock_screening_repo.save.await_count == 2


@pytest.mark.asyncio
async def test_skips_duplicate_screening() -> None:
    """Test that an existing screening is skipped, not updated."""
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.side_effect = ScreeningAlreadyExistsError(
        "Screening already exists"
    )

    rows = (_make_screening_input(cinema_id="cin-123"),)

    result = await _run(
        CreateScreeningsCommand(screening_repository=mock_screening_repo),
        rows,
    )

    assert result.total_count == 0
    assert result.imported_count == 0
    assert result.updated_count == 0
    assert result.skipped_count == 1
    mock_screening_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_skips_external_id_conflict() -> None:
    """Test that a single external_id collision is skipped, not fatal."""
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.side_effect = [
        ScreeningAlreadyExistsError(
            "A screening with external_id='486899' already exists"
        ),
        None,
    ]

    rows = (
        _make_screening_input(
            movie_id="mov-a",
            movie_title="Movie A",
            external_id="486899",
        ),
        _make_screening_input(
            movie_id="mov-b",
            movie_title="Movie B",
            external_id="486900",
        ),
    )

    result = await _run(
        CreateScreeningsCommand(screening_repository=mock_screening_repo),
        rows,
    )

    assert result.total_count == 1
    assert result.imported_count == 1
    assert result.updated_count == 0
    assert result.skipped_count == 1
    assert result.screenings[0].movie_title == "Movie B"


@pytest.mark.asyncio
async def test_passes_movie_and_cinema_data_to_screening() -> None:
    """Test that the screening entity receives the correct movie/cinema IDs."""
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.return_value = None

    rows = (
        _make_screening_input(
            movie_id="mov-special",
            movie_title="Special Movie",
            cinema_id="cin-456",
            cinema_name="Cinéma du Parc",
        ),
    )

    await _run(
        CreateScreeningsCommand(screening_repository=mock_screening_repo),
        rows,
    )

    created_screening = mock_screening_repo.save.call_args[0][0]
    assert created_screening.movie.id == MovieId(value="mov-special")
    assert created_screening.movie.title == "Special Movie"
    assert str(created_screening.cinema.id) == "cin-456"
    assert created_screening.cinema.name == "Cinéma du Parc"


def test_screening_input_validates_empty_movie_id() -> None:
    """Verify ScreeningInput rejects empty movie_id."""
    with pytest.raises(ValueError, match="movie_id must not be empty"):
        _make_screening_input(movie_id="")


def test_screening_input_validates_empty_cinema_id() -> None:
    """Verify ScreeningInput rejects empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        _make_screening_input(cinema_id="")


def test_screening_input_validates_naive_showtime() -> None:
    """Verify ScreeningInput rejects naive datetime."""
    with pytest.raises(ValueError, match="showtime must be timezone-aware"):
        _make_screening_input(showtime=datetime(2026, 6, 7, 19, 30, 0))


@pytest.mark.asyncio
async def test_output_data_rejects_negative_counts() -> None:
    """Verify OutputData validation rejects negative counts."""
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    command = CreateScreeningsCommand(screening_repository=mock_screening_repo)

    with pytest.raises(ValueError, match="total_count must not be negative"):
        command.OutputData(
            screenings=(),
            total_count=-1,
            imported_count=0,
            updated_count=0,
            skipped_count=0,
        )
