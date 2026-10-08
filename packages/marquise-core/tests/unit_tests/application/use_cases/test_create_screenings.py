"""Input and batch failure contracts for CreateScreeningsCommand."""

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand


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


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["read_import_candidates", "commit_import"])
async def test_unexpected_failure_is_not_skipped(operation: str) -> None:
    """Unexpected storage failures abort rather than becoming skipped rows."""
    repository = create_autospec(ScreeningRepository, instance=True)
    repository.read_import_candidates.return_value = ()
    getattr(repository, operation).side_effect = RuntimeError("Database unavailable")
    with pytest.raises(RuntimeError, match="Database unavailable"):
        await _run(CreateScreeningsCommand(repository), (_make_screening_input(),))
