"""Tests for UpsertScreeningsCommand."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningAlreadyExistsError
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
)
from marquise.application.use_cases.upsert_screenings import UpsertScreeningsCommand
from marquise.domain.entities import Cinema, Movie
from marquise.domain.value_objects import CinemaId, MovieId


def _make_screening_row(
    movie_title: str = "Test Movie",
    showtime: datetime | None = None,
    external_id: str | None = None,
) -> UpsertScreeningsCommand.ScreeningRow:
    return UpsertScreeningsCommand.ScreeningRow(
        movie_title=movie_title,
        showtime=showtime or datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        external_id=external_id,
        ticket_url=None,
        room=None,
        language=None,
    )


CINEMA = Cinema(id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal")


async def _run(
    command: UpsertScreeningsCommand,
    rows: tuple[UpsertScreeningsCommand.ScreeningRow, ...],
    cinema_id: str = "cin-123",
    movie_lookup: dict[str, str] | None = None,
) -> UpsertScreeningsCommand.OutputData:
    return await command.execute(
        UpsertScreeningsCommand.InputData(
            rows=rows,
            cinema_id=cinema_id,
            movie_lookup=movie_lookup or {},
        )
    )


@pytest.mark.asyncio
async def test_creates_new_screenings() -> None:
    """Test that new screenings are created and counted as imported."""
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.return_value = (None, True)
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = CINEMA
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_id.side_effect = lambda mid: (
        Movie(id=MovieId(value="mov-a"), title="Movie A")
        if mid == MovieId(value="mov-a")
        else Movie(id=MovieId(value="mov-b"), title="Movie B")
    )

    rows = (
        _make_screening_row("Movie A", datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)),
        _make_screening_row("Movie B", datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC)),
    )

    result = await _run(
        UpsertScreeningsCommand(
            screening_repository=mock_screening_repo,
            cinema_repository=mock_cinema_repo,
            movie_repository=mock_movie_repo,
        ),
        rows,
        movie_lookup={"Movie A": "mov-a", "Movie B": "mov-b"},
    )

    assert result.total_count == 2
    assert result.imported_count == 2
    assert result.updated_count == 0
    assert result.skipped_count == 0
    assert result.screenings[0].imported is True
    assert result.screenings[1].imported is True
    assert mock_screening_repo.save.await_count == 2
    mock_screening_repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_updates_existing_screening() -> None:
    """Test that an existing screening triggers update on the repository."""
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.return_value = (None, False)
    mock_screening_repo.update.return_value = None
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = CINEMA
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_id.return_value = Movie(
        id=MovieId(value="mov-existing"), title="Existing Movie"
    )

    rows = (_make_screening_row("Existing Movie"),)

    result = await _run(
        UpsertScreeningsCommand(
            screening_repository=mock_screening_repo,
            cinema_repository=mock_cinema_repo,
            movie_repository=mock_movie_repo,
        ),
        rows,
        movie_lookup={"Existing Movie": "mov-existing"},
    )

    assert result.total_count == 1
    assert result.imported_count == 0
    assert result.updated_count == 1
    assert result.screenings[0].imported is False
    mock_screening_repo.save.assert_awaited_once()
    mock_screening_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_skips_external_id_conflict() -> None:
    """Test that a single external_id collision is skipped, not fatal.

    Reproduces the Cineplex bug where a reused/rescheduled external_id
    (source-native session ID) collides with a screening already stored
    under a different (cinema_id, movie_id, showtime): the whole batch
    must not abort, and the other screenings must still succeed.
    """
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.side_effect = [
        ScreeningAlreadyExistsError(
            "A screening with external_id='486899' already exists for a "
            "different (cinema_id, movie_id, showtime)"
        ),
        (None, True),
    ]
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = CINEMA
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_movie_repo.find_by_id.side_effect = lambda mid: (
        Movie(id=MovieId(value="mov-a"), title="Movie A")
        if mid == MovieId(value="mov-a")
        else Movie(id=MovieId(value="mov-b"), title="Movie B")
    )

    rows = (
        _make_screening_row(
            "Movie A",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            external_id="486899",
        ),
        _make_screening_row(
            "Movie B",
            datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC),
            external_id="486900",
        ),
    )

    result = await _run(
        UpsertScreeningsCommand(
            screening_repository=mock_screening_repo,
            cinema_repository=mock_cinema_repo,
            movie_repository=mock_movie_repo,
        ),
        rows,
        movie_lookup={"Movie A": "mov-a", "Movie B": "mov-b"},
    )

    assert result.total_count == 1
    assert result.imported_count == 1
    assert result.updated_count == 0
    assert result.skipped_count == 1
    assert result.screenings[0].movie_title == "Movie B"
