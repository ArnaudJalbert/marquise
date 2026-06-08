"""Tests for ImportScreeningsUseCase."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    MovieRepository,
    ScreeningRepository,
    SourceDefinitionRepository,
    SourceRegistryQuery,
)
from marquise.application.repositories.source_registry_query import ShowtimeRow
from marquise.application.use_cases.import_screenings import (
    ImportedScreeningData,
    ImportScreeningsUseCase,
)
from marquise.domain.entities import (
    Cinema,
    CinemaSourceAssignment,
    Movie,
    SourceDefinition,
)
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    SourceName,
)


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide a sample Cinema for tests."""
    return Cinema(
        id=CinemaId(value="cin-123"),
        name="Cinéma Beaubien",
        city="Montreal",
    )


def _make_showtime_row(
    movie_title: str = "Test Movie",
    showtime: datetime | None = None,
    price: float | None = 14.99,
) -> ShowtimeRow:
    return ShowtimeRow(
        movie_title=movie_title,
        showtime=showtime or datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc),
        price=price,
        available_seats=None,
    )


@pytest.mark.asyncio
async def test_import_screenings_creates_new_screenings() -> None:
    """Test that new screenings are created from source data."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_source_def_repo = create_autospec(SourceDefinitionRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"),
        name="Cinéma Beaubien",
        city="Montreal",
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    assignment = CinemaSourceAssignment(
        cinema_id=CinemaId(value="cin-123"),
        source_name=SourceName(value="cinemacinema"),
    )
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    mock_source_def_repo.find_by_name.return_value = source_definition

    rows = [
        _make_showtime_row(
            "Movie A",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc),
            14.99,
        ),
        _make_showtime_row(
            "Movie B",
            datetime(2026, 6, 7, 21, 0, 0, tzinfo=timezone.utc),
            12.50,
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows

    mock_movie_repo.find_by_title.side_effect = [None, None]
    movie_a = Movie(
        id=MovieId(value="mov-a"),
        title="Movie A",
        release_date=date(2026, 6, 7),
        directors=None,
        cast=None,
    )
    movie_b = Movie(
        id=MovieId(value="mov-b"),
        title="Movie B",
        release_date=date(2026, 6, 7),
        directors=None,
        cast=None,
    )
    mock_movie_repo.save.side_effect = [movie_a, movie_b]

    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_definition_repository=mock_source_def_repo,
        source_registry=mock_registry,
        movie_repository=mock_movie_repo,
        screening_repository=mock_screening_repo,
    )

    request = ImportScreeningsUseCase.InputData(
        cinema_id="cin-123",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 7),
    )
    result = await use_case.execute(request)

    assert result.cinema_id == "cin-123"
    assert result.cinema_name == "Cinéma Beaubien"
    assert result.source_name == "cinemacinema"
    assert result.total_count == 2
    assert result.imported_count == 2
    assert result.updated_count == 0
    assert result.screenings[0].imported is True
    assert result.screenings[1].imported is True

    mock_cinema_repo.find_by_id.assert_awaited_once_with(CinemaId(value="cin-123"))
    mock_assignment_repo.find_by_cinema_id.assert_awaited_once_with(
        CinemaId(value="cin-123")
    )
    mock_source_def_repo.find_by_name.assert_awaited_once_with(
        SourceName(value="cinemacinema")
    )
    mock_registry.fetch_showtimes.assert_awaited_once_with(
        cinema=cinema,
        source_definition=source_definition,
        start_date=datetime(2026, 6, 7, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 7, 23, 59, 59, 999999, tzinfo=timezone.utc),
    )
    assert mock_movie_repo.save.await_count == 2
    assert mock_screening_repo.save.await_count == 2


@pytest.mark.asyncio
async def test_import_screenings_reuses_existing_movie() -> None:
    """Test that an existing movie is reused (not created again)."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)
    mock_source_def_repo = create_autospec(SourceDefinitionRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"),
        name="Cinéma Beaubien",
        city="Montreal",
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    assignment = CinemaSourceAssignment(
        cinema_id=CinemaId(value="cin-123"),
        source_name=SourceName(value="cinemacinema"),
    )
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    mock_source_def_repo.find_by_name.return_value = source_definition

    rows = [
        _make_showtime_row(
            "Movie A",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc),
            14.99,
        )
    ]
    mock_registry.fetch_showtimes.return_value = rows

    movie_a = Movie(
        id=MovieId(value="mov-a"),
        title="Movie A",
        release_date=date(2026, 6, 7),
        directors=None,
        cast=None,
    )
    mock_movie_repo.find_by_title.return_value = movie_a

    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_definition_repository=mock_source_def_repo,
        source_registry=mock_registry,
        movie_repository=mock_movie_repo,
        screening_repository=mock_screening_repo,
    )

    request = ImportScreeningsUseCase.InputData(
        cinema_id="cin-123",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 7),
    )
    result = await use_case.execute(request)

    assert result.total_count == 1

    mock_movie_repo.find_by_title.assert_awaited()
    mock_movie_repo.save.assert_not_awaited()
    mock_screening_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_screenings_raises_when_cinema_not_found() -> None:
    """Test that CinemaNotFoundError is raised when cinema doesn't exist."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = None

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=create_autospec(
            CinemaSourceAssignmentRepository, instance=True
        ),
        source_definition_repository=create_autospec(
            SourceDefinitionRepository, instance=True
        ),
        source_registry=create_autospec(SourceRegistryQuery, instance=True),
        movie_repository=create_autospec(MovieRepository, instance=True),
        screening_repository=create_autospec(ScreeningRepository, instance=True),
    )

    request = ImportScreeningsUseCase.InputData(
        cinema_id="cin-999",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 7),
    )
    with pytest.raises(CinemaNotFoundError, match="cin-999"):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_import_screenings_raises_when_no_assignment() -> None:
    """Test that CinemaSourceAssignmentNotFoundError is raised."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = Cinema(
        id=CinemaId(value="cin-123"),
        name="Cinéma Beaubien",
        city="Montreal",
    )
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_assignment_repo.find_by_cinema_id.return_value = None

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_definition_repository=create_autospec(
            SourceDefinitionRepository, instance=True
        ),
        source_registry=create_autospec(SourceRegistryQuery, instance=True),
        movie_repository=create_autospec(MovieRepository, instance=True),
        screening_repository=create_autospec(ScreeningRepository, instance=True),
    )

    request = ImportScreeningsUseCase.InputData(
        cinema_id="cin-123",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 7),
    )
    with pytest.raises(CinemaSourceAssignmentNotFoundError):
        await use_case.execute(request)


def test_input_data_rejects_empty_cinema_id() -> None:
    """Test InputData rejects empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        ImportScreeningsUseCase.InputData(
            cinema_id="",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )


def test_input_data_rejects_whitespace_cinema_id() -> None:
    """Test InputData rejects whitespace-only cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        ImportScreeningsUseCase.InputData(
            cinema_id="   ",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )


def test_input_data_rejects_start_date_after_end_date() -> None:
    """Test InputData rejects start_date after end_date."""
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        ImportScreeningsUseCase.InputData(
            cinema_id="cin-123",
            start_date=date(2026, 6, 8),
            end_date=date(2026, 6, 7),
        )


def test_input_data_allows_valid_input() -> None:
    """Test InputData accepts valid input."""
    request = ImportScreeningsUseCase.InputData(
        cinema_id="cin-123",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 7),
    )
    assert request.cinema_id == "cin-123"
    assert request.start_date == date(2026, 6, 7)
    assert request.end_date == date(2026, 6, 7)


def test_output_data_rejects_empty_cinema_id() -> None:
    """Test OutputData rejects empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        ImportScreeningsUseCase.OutputData(
            cinema_id="",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=0,
            imported_count=0,
            updated_count=0,
        )


def test_output_data_rejects_empty_cinema_name() -> None:
    """Test OutputData rejects empty cinema_name."""
    with pytest.raises(ValueError, match="cinema_name must not be empty"):
        ImportScreeningsUseCase.OutputData(
            cinema_id="cin-123",
            cinema_name="",
            source_name="cinemacinema",
            screenings=(),
            total_count=0,
            imported_count=0,
            updated_count=0,
        )


def test_output_data_rejects_empty_source_name() -> None:
    """Test OutputData rejects empty source_name."""
    with pytest.raises(ValueError, match="source_name must not be empty"):
        ImportScreeningsUseCase.OutputData(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="",
            screenings=(),
            total_count=0,
            imported_count=0,
            updated_count=0,
        )


def test_output_data_rejects_negative_total_count() -> None:
    """Test OutputData rejects negative total_count."""
    with pytest.raises(ValueError, match="total_count must not be negative"):
        ImportScreeningsUseCase.OutputData(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=-1,
            imported_count=0,
            updated_count=0,
        )


def test_output_data_allows_valid() -> None:
    """Test OutputData accepts valid data."""
    screening = ImportedScreeningData(
        movie_title="Movie A",
        showtime="2026-06-07T19:30:00+00:00",
        price=14.99,
        imported=True,
    )
    result = ImportScreeningsUseCase.OutputData(
        cinema_id="cin-123",
        cinema_name="Cinéma Beaubien",
        source_name="cinemacinema",
        screenings=(screening,),
        total_count=1,
        imported_count=1,
        updated_count=0,
    )
    assert result.cinema_id == "cin-123"
    assert result.cinema_name == "Cinéma Beaubien"
    assert result.source_name == "cinemacinema"
    assert result.total_count == 1
    assert result.imported_count == 1
    assert result.updated_count == 0
    assert len(result.screenings) == 1


def test_imported_screening_data_rejects_empty_movie_title() -> None:
    """Test ImportedScreeningData rejects empty movie_title."""
    with pytest.raises(ValueError, match="movie_title must not be empty"):
        ImportedScreeningData(
            movie_title="",
            showtime="2026-06-07T19:30:00+00:00",
            price=14.99,
            imported=True,
        )


def test_imported_screening_data_rejects_empty_showtime() -> None:
    """Test ImportedScreeningData rejects empty showtime."""
    with pytest.raises(ValueError, match="showtime must not be empty"):
        ImportedScreeningData(
            movie_title="Movie A",
            showtime="",
            price=14.99,
            imported=True,
        )


def test_showtime_row_creation() -> None:
    """Test ShowtimeRow dataclass creation."""
    showtime = datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc)
    row = ShowtimeRow(
        movie_title="Test Movie",
        showtime=showtime,
        price=14.99,
        available_seats=50,
    )
    assert row.movie_title == "Test Movie"
    assert row.showtime == showtime
    assert row.price == 14.99
    assert row.available_seats == 50


def test_showtime_row_allows_none_values() -> None:
    """Test ShowtimeRow allows None price and available_seats."""
    showtime = datetime(2026, 6, 7, 19, 30, 0, tzinfo=timezone.utc)
    row = ShowtimeRow(
        movie_title="Test Movie",
        showtime=showtime,
        price=None,
        available_seats=None,
    )
    assert row.price is None
    assert row.available_seats is None
