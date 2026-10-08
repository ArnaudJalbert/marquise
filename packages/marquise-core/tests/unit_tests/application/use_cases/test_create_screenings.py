"""Tests for CreateScreeningsCommand."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import create_autospec
from zoneinfo import ZoneInfo

import pytest

from marquise.application.exceptions import (
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
)
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
async def test_updates_existing_screening() -> None:
    """Test that an existing screening is updated instead of skipped."""
    from marquise.domain.entities import Screening as ScreeningEntity

    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.side_effect = ScreeningAlreadyExistsError(
        "Screening already exists"
    )
    mock_screening_repo.update.return_value = create_autospec(
        ScreeningEntity, instance=True
    )

    rows = (_make_screening_input(cinema_id="cin-123"),)

    result = await _run(
        CreateScreeningsCommand(screening_repository=mock_screening_repo),
        rows,
    )

    assert result.total_count == 1
    assert result.imported_count == 0
    assert result.updated_count == 1
    assert result.skipped_count == 0
    mock_screening_repo.save.assert_awaited_once()
    mock_screening_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_reschedules_same_source_screening() -> None:
    """A same-day source collision moves existing screening in place."""
    repo = create_autospec(ScreeningRepository, instance=True)
    repo.save.side_effect = ScreeningExternalIdConflictError("collision")
    repo.reschedule.return_value = create_autospec(object, instance=True)

    row = _make_screening_input(external_id="show-1")
    row = CreateScreeningsCommand.ScreeningInput(
        movie_id=row.movie_id,
        movie_title=row.movie_title,
        cinema_id=row.cinema_id,
        cinema_name=row.cinema_name,
        showtime=row.showtime,
        external_id=row.external_id,
        source_name="cineplex",
    )
    result = await _run(CreateScreeningsCommand(repo), (row,))

    assert result.rescheduled_count == 1
    assert result.updated_count == 0
    assert result.screenings[0].rescheduled is True
    repo.reschedule.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("showtime", "start", "end"),
    [
        (
            datetime(2026, 3, 8, 22, tzinfo=UTC),
            datetime(2026, 3, 8, 5, tzinfo=UTC),
            datetime(2026, 3, 9, 4, tzinfo=UTC),
        ),
        (
            datetime(2026, 11, 1, 23, tzinfo=UTC),
            datetime(2026, 11, 1, 4, tzinfo=UTC),
            datetime(2026, 11, 2, 5, tzinfo=UTC),
        ),
    ],
)
async def test_reschedule_uses_local_midnights_across_dst(
    showtime: datetime, start: datetime, end: datetime
) -> None:
    """Spring/fall reschedules use 23/25-hour local days, not UTC plus 24 hours."""
    repo = create_autospec(ScreeningRepository, instance=True)
    repo.save.side_effect = ScreeningExternalIdConflictError("collision")
    row = replace(
        _make_screening_input(showtime=showtime, external_id="show-1"),
        source_name="cineplex",
    )

    result = await _run(CreateScreeningsCommand(repo), (row,))

    assert result.rescheduled_count == 1
    assert repo.reschedule.await_args.kwargs["local_day_start"] == start
    assert repo.reschedule.await_args.kwargs["local_day_end"] == end


@pytest.mark.asyncio
async def test_refuses_reschedule_without_matching_source() -> None:
    """A source mismatch leaves external-ID collision unresolved."""
    repo = create_autospec(ScreeningRepository, instance=True)
    repo.save.side_effect = ScreeningExternalIdConflictError("collision")
    repo.reschedule.return_value = None
    base = _make_screening_input(external_id="show-1")
    row = CreateScreeningsCommand.ScreeningInput(
        movie_id=base.movie_id,
        movie_title=base.movie_title,
        cinema_id=base.cinema_id,
        cinema_name=base.cinema_name,
        showtime=base.showtime,
        external_id=base.external_id,
        source_name="cineplex",
    )

    result = await _run(CreateScreeningsCommand(repo), (row,))

    assert result.skipped_count == 1
    assert result.rescheduled_count == 0


@pytest.mark.asyncio
async def test_ambiguous_batch_ownership_is_skipped_before_writing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One source ID naming two performances cannot overwrite either of them."""
    repo = create_autospec(ScreeningRepository, instance=True)
    first = replace(_make_screening_input(external_id="show-1"), source_name="cineplex")
    second = replace(first, showtime=datetime(2026, 6, 7, 20, tzinfo=UTC))

    result = await _run(CreateScreeningsCommand(repo), (first, second))

    assert result.skipped_count == 2
    assert result.total_count == 0
    repo.save.assert_not_awaited()
    repo.reschedule.assert_not_awaited()
    assert "Ambiguous" in caplog.text


@pytest.mark.asyncio
async def test_skips_external_id_conflict() -> None:
    """An insert collision is skipped without trying to update another row."""
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_screening_repo.save.side_effect = [
        ScreeningExternalIdConflictError(
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
    mock_screening_repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_skips_update_external_id_conflict(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An update collision warns and skips while unrelated rows still import."""
    repo = create_autospec(ScreeningRepository, instance=True)
    repo.save.side_effect = [ScreeningAlreadyExistsError("Existing row"), None]
    repo.update.side_effect = ScreeningExternalIdConflictError(
        "external_id='494935' belongs to another screening"
    )
    rows = (
        _make_screening_input(external_id="494935"),
        _make_screening_input(movie_id="mov-b", movie_title="Movie B"),
    )

    result = await _run(CreateScreeningsCommand(repo), rows)

    assert result.total_count == result.imported_count == 1
    assert result.updated_count == 0
    assert result.skipped_count == 1
    assert result.screenings[0].movie_title == "Movie B"
    repo.update.assert_awaited_once()
    assert "494935" in caplog.text
    assert "cin-123" in caplog.text
    assert "mov-a" in caplog.text
    assert "2026-06-07T19:30:00+00:00" in caplog.text
    assert "belongs to another screening" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["save", "update"])
async def test_unexpected_failure_is_not_skipped(operation: str) -> None:
    """Unexpected save/update failures abort instead of becoming skipped rows."""
    repo = create_autospec(ScreeningRepository, instance=True)
    error = RuntimeError("Database unavailable")
    if operation == "save":
        repo.save.side_effect = error
    else:
        repo.save.side_effect = ScreeningAlreadyExistsError("Existing row")
        repo.update.side_effect = error

    with pytest.raises(RuntimeError, match="Database unavailable") as raised:
        await _run(CreateScreeningsCommand(repo), (_make_screening_input(),))

    assert raised.value is error


@pytest.mark.asyncio
async def test_skips_existing_screening_deleted_before_update() -> None:
    """A row deleted between save and update remains a counted skip."""
    repo = create_autospec(ScreeningRepository, instance=True)
    repo.save.side_effect = ScreeningAlreadyExistsError("Existing row")
    repo.update.return_value = None

    result = await _run(CreateScreeningsCommand(repo), (_make_screening_input(),))

    assert result.skipped_count == 1
    assert result.total_count == result.imported_count == result.updated_count == 0


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
async def test_dst_fold_inputs_are_ambiguous_without_persistence() -> None:
    """Repeated DST clock times are distinct instants and cannot share a native ID."""
    repository = create_autospec(ScreeningRepository, instance=True)
    zone = ZoneInfo("America/Montreal")
    first = _make_screening_input(
        showtime=datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0),
        external_id="shared",
    )
    second = replace(first, showtime=first.showtime.replace(fold=1))
    result = await _run(CreateScreeningsCommand(repository), (first, second))

    assert result.skipped_count == 2
    repository.save.assert_not_awaited()
    repository.update.assert_not_awaited()
    repository.reschedule.assert_not_awaited()


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
