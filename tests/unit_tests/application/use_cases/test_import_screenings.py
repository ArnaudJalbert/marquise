"""Tests for ImportScreeningsUseCase."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
    ScreeningAlreadyExistsError,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    MovieRepository,
    ScreeningRepository,
    SourceRegistryQuery,
)
from marquise.application.repositories.source_registry_query import (
    MovieEnrichmentData,
    ShowtimeRow,
)
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
    identifier: str | None = None,
    external_id: str | None = None,
    ticket_url: str | None = None,
    room: str | None = None,
    language: str | None = None,
) -> ShowtimeRow:
    return ShowtimeRow(
        movie_title=movie_title,
        showtime=showtime or datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        identifier=identifier,
        external_id=external_id,
        ticket_url=ticket_url,
        room=room,
        language=language,
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

    cinema = Cinema(
        id=CinemaId(value="cin-123"),
        name="Cinéma Beaubien",
        city="Montreal",
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [
        _make_showtime_row("Movie A", datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)),
        _make_showtime_row("Movie B", datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC)),
    ]
    mock_registry.fetch_showtimes.return_value = rows

    mock_movie_repo.find_by_title.side_effect = [None, None]
    movie_a = Movie(
        id=MovieId(value="mov-a"),
        title="Movie A",
    )
    movie_b = Movie(
        id=MovieId(value="mov-b"),
        title="Movie B",
    )
    mock_movie_repo.save.side_effect = [movie_a, movie_b]

    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
    mock_registry.fetch_showtimes.assert_awaited_once_with(
        cinema=cinema,
        source_definition=source_definition,
        start_date=datetime(2026, 6, 7, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 7, 23, 59, 59, 999999, tzinfo=UTC),
    )
    assert mock_movie_repo.save.await_count == 2
    assert mock_screening_repo.save.await_count == 2


@pytest.mark.asyncio
async def test_import_screenings_skips_external_id_conflict() -> None:
    """Test that a single external_id collision is skipped, not fatal.

    Reproduces the Cineplex bug where a reused/rescheduled external_id
    (source-native session ID) collides with a screening already stored
    under a different (cinema_id, movie_id, showtime): the whole cinema
    import must not abort, and the other screenings must still succeed.
    """
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"),
        name="Cinéma Cineplex Forum et VIP",
        city="Montreal",
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [
        _make_showtime_row(
            "Movie A",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            external_id="486899",
        ),
        _make_showtime_row(
            "Movie B",
            datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC),
            external_id="486900",
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows

    movie_a = Movie(id=MovieId(value="mov-a"), title="Movie A")
    movie_b = Movie(id=MovieId(value="mov-b"), title="Movie B")
    mock_movie_repo.find_by_title.side_effect = [None, None]
    mock_movie_repo.save.side_effect = [movie_a, movie_b]

    mock_screening_repo.save.side_effect = [
        ScreeningAlreadyExistsError(
            "A screening with external_id='486899' already exists for a "
            "different (cinema_id, movie_id, showtime)"
        ),
        (None, True),
    ]

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
    assert result.imported_count == 1
    assert result.updated_count == 0
    assert result.skipped_count == 1
    assert result.screenings[0].movie_title == "Movie B"


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

    cinema = Cinema(
        id=CinemaId(value="cin-123"),
        name="Cinéma Beaubien",
        city="Montreal",
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [_make_showtime_row("Movie A", datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC))]
    mock_registry.fetch_showtimes.return_value = rows

    movie_a = Movie(
        id=MovieId(value="mov-a"),
        title="Movie A",
    )
    mock_movie_repo.find_by_title.return_value = movie_a

    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
async def test_import_screenings_dedupes_titles_differing_by_whitespace() -> None:
    """Test that titles differing only by whitespace share a single movie."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [
        _make_showtime_row(
            "Beau Is Afraid",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        ),
        _make_showtime_row(
            "  Beau  Is  Afraid ",
            datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC),
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows
    mock_movie_repo.find_by_title.side_effect = [None, None]

    saved_movie = Movie(id=MovieId(value="mov-a"), title="Beau Is Afraid")
    mock_movie_repo.save.return_value = saved_movie
    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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

    assert result.total_count == 2
    # Both rows normalize to the same title, so only one movie gets created
    # even though find_by_title is still queried once per row.
    mock_movie_repo.find_by_title.assert_any_await("Beau Is Afraid")
    mock_movie_repo.save.assert_awaited_once()
    created_movie = mock_movie_repo.save.call_args[0][0]
    assert created_movie.title == "Beau Is Afraid"


@pytest.mark.asyncio
async def test_import_screenings_reuses_movie_found_with_different_case() -> None:
    """Test that a case-insensitive match still enriches and re-links correctly.

    Regression test: re-keying the movie lookup by the *saved entity's* title
    (rather than the query title) after a case-insensitive find_by_title match
    would silently orphan the row's own lookup key, losing the enrichment.
    """
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [
        _make_showtime_row(
            "The Batman",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            identifier="the-batman-slug",
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows

    # Stored under a different case than today's scrape, and missing
    # optional fields so it qualifies for enrichment.
    existing_movie = Movie(id=MovieId(value="mov-batman"), title="the batman")
    mock_movie_repo.find_by_title.return_value = existing_movie

    enrichment = MovieEnrichmentData(description="The Dark Knight returns")
    mock_registry.fetch_movie_detail.return_value = enrichment

    enriched_movie = Movie(
        id=MovieId(value="mov-batman"),
        title="the batman",
        description="The Dark Knight returns",
    )
    mock_movie_repo.save.return_value = enriched_movie
    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
    # The screening must be linked to the enriched movie, not lost because
    # the lookup key and the saved entity's title differ in case.
    saved_screening = mock_screening_repo.save.call_args[0][0]
    assert saved_screening.movie.description == "The Dark Knight returns"


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


def test_output_data_rejects_negative_imported_count() -> None:
    """Test OutputData rejects negative imported_count."""
    with pytest.raises(ValueError, match="imported_count must not be negative"):
        ImportScreeningsUseCase.OutputData(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=0,
            imported_count=-1,
            updated_count=0,
        )


def test_output_data_rejects_negative_updated_count() -> None:
    """Test OutputData rejects negative updated_count."""
    with pytest.raises(ValueError, match="updated_count must not be negative"):
        ImportScreeningsUseCase.OutputData(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=0,
            imported_count=0,
            updated_count=-1,
        )


def test_output_data_rejects_negative_skipped_count() -> None:
    """Test OutputData rejects negative skipped_count."""
    with pytest.raises(ValueError, match="skipped_count must not be negative"):
        ImportScreeningsUseCase.OutputData(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=0,
            imported_count=0,
            updated_count=0,
            skipped_count=-1,
        )


def test_output_data_allows_valid() -> None:
    """Test OutputData accepts valid data."""
    screening = ImportedScreeningData(
        movie_title="Movie A",
        showtime="2026-06-07T19:30:00+00:00",
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
            imported=True,
        )


def test_imported_screening_data_rejects_empty_showtime() -> None:
    """Test ImportedScreeningData rejects empty showtime."""
    with pytest.raises(ValueError, match="showtime must not be empty"):
        ImportedScreeningData(
            movie_title="Movie A",
            showtime="",
            imported=True,
        )


def test_showtime_row_creation() -> None:
    """Test ShowtimeRow dataclass creation."""
    showtime = datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    row = ShowtimeRow(
        movie_title="Test Movie",
        showtime=showtime,
    )
    assert row.movie_title == "Test Movie"
    assert row.showtime == showtime


@pytest.mark.asyncio
async def test_import_updates_existing_screening() -> None:
    """Test that an existing screening triggers update on the repository."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [
        _make_showtime_row(
            "Existing Movie",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows

    movie = Movie(id=MovieId(value="mov-existing"), title="Existing Movie")
    mock_movie_repo.find_by_title.return_value = movie
    mock_movie_repo.save.return_value = movie

    mock_screening_repo.save.return_value = (None, False)
    mock_screening_repo.update.return_value = None

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
    assert result.imported_count == 0
    assert result.updated_count == 1
    assert result.screenings[0].imported is False
    mock_screening_repo.save.assert_awaited_once()
    mock_screening_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_enriches_movie_with_all_fields() -> None:
    """Test that enrichment populates all optional fields."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [
        _make_showtime_row(
            "Rich Movie",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            identifier="rich-slug",
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows
    mock_movie_repo.find_by_title.return_value = None

    enrichment = MovieEnrichmentData(
        description="A rich movie",
        directors=("Director",),
        cast=("Actor A", "Actor B"),
        duration_minutes=100,
        release_year=2026,
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres=("Drama", "Thriller"),
        original_title="Original Title",
        rating="PG-13",
        origin_countries=("US", "UK"),
    )
    mock_registry.fetch_movie_detail.return_value = enrichment

    saved_movie = Movie(
        id=MovieId(value="mov-rich"),
        title="Rich Movie",
        description="A rich movie",
        directors=("Director",),
        cast=("Actor A", "Actor B"),
        duration_minutes=100,
        release_year=2026,
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres=("Drama", "Thriller"),
        original_title="Original Title",
        rating="PG-13",
        origin_countries=("US", "UK"),
    )
    mock_movie_repo.save.return_value = saved_movie
    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
    saved = mock_movie_repo.save.call_args[0][0]
    assert saved.description == "A rich movie"
    assert saved.directors == ("Director",)
    assert saved.cast == ("Actor A", "Actor B")
    assert saved.duration_minutes == 100
    assert saved.release_year == 2026
    assert saved.poster_url == "https://example.com/poster.jpg"
    assert saved.trailer_url == "https://example.com/trailer"
    assert saved.genres == ("Drama", "Thriller")
    assert saved.original_title == "Original Title"
    assert saved.rating == "PG-13"
    assert saved.origin_countries == ("US", "UK")
    """Test ShowtimeRow dataclass creation."""
    showtime = datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    row = ShowtimeRow(
        movie_title="Test Movie",
        showtime=showtime,
    )
    assert row.movie_title == "Test Movie"
    assert row.showtime == showtime


@pytest.mark.asyncio
async def test_import_enriches_new_movies_with_identifier() -> None:
    """Test that new movies with identifiers are enriched from the source."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [
        _make_showtime_row(
            "New Movie",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            identifier="new-movie-slug",
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows

    mock_movie_repo.find_by_title.return_value = None

    enrichment = MovieEnrichmentData(
        description="A great new movie",
        duration_minutes=120,
        directors=("Director A",),
        release_year=2026,
    )
    mock_registry.fetch_movie_detail.return_value = enrichment

    saved_movie = Movie(
        id=MovieId(value="mov-new"),
        title="New Movie",
        description="A great new movie",
        duration_minutes=120,
        directors=("Director A",),
        release_year=2026,
    )
    mock_movie_repo.save.return_value = saved_movie
    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
    assert result.imported_count == 1
    mock_registry.fetch_movie_detail.assert_awaited_once_with(
        "cinemacinema", "new-movie-slug"
    )
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_enriches_existing_movie_with_null_fields() -> None:
    """Test that an existing movie with null fields gets enriched."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    existing_movie = Movie(
        id=MovieId(value="mov-existing"),
        title="Existing Movie",
        directors=("Old Director",),
        description=None,
        duration_minutes=None,
    )

    rows = [
        _make_showtime_row(
            "Existing Movie",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            identifier="existing-slug",
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows
    mock_movie_repo.find_by_title.return_value = existing_movie

    enrichment = MovieEnrichmentData(
        description="An existing movie with new details",
        duration_minutes=130,
    )
    mock_registry.fetch_movie_detail.return_value = enrichment
    mock_movie_repo.save.return_value = Movie(
        id=MovieId(value="mov-existing"),
        title="Existing Movie",
        directors=("Old Director",),
        description="An existing movie with new details",
        duration_minutes=130,
    )
    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
    mock_registry.fetch_movie_detail.assert_awaited_once_with(
        "cinemacinema", "existing-slug"
    )
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_does_not_refetch_already_enriched_movie() -> None:
    """Test that an already-enriched movie is not fetched again."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    enriched_movie = Movie(
        id=MovieId(value="mov-enriched"),
        title="Full Movie",
        directors=("Director",),
        cast=("Actor",),
        duration_minutes=120,
        description="Already known",
        release_year=2025,
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres=("Drama",),
        original_title="Full Movie",
        rating="PG",
        origin_countries=("US",),
    )

    rows = [
        _make_showtime_row(
            "Full Movie",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            identifier="full-slug",
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows
    mock_movie_repo.find_by_title.return_value = enriched_movie
    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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
    mock_registry.fetch_movie_detail.assert_not_awaited()
    mock_movie_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_handles_mixed_identifiers_for_enrichment() -> None:
    """Test enrichment alignment when some movies have identifiers and some don't.

    This regression test validates the fix for the enrichment misalignment bug
    where ``enrich_identifiers`` was shorter than ``enrich_titles``, causing
    enrichment results to be applied to the wrong movie.
    """
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_screening_repo = create_autospec(ScreeningRepository, instance=True)

    cinema = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_cinema_repo.find_by_id.return_value = cinema

    source_definition = SourceDefinition(
        name=SourceName(value="cinemacinema"),
        display_name="Cinema Cinema",
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source_definition)
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    rows = [
        _make_showtime_row(
            "Movie With ID",
            datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            identifier="has-id",
        ),
        _make_showtime_row(
            "Movie Without ID",
            datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC),
            identifier=None,
        ),
    ]
    mock_registry.fetch_showtimes.return_value = rows
    mock_movie_repo.find_by_title.side_effect = [None, None]

    enrichment = MovieEnrichmentData(
        description="Only movie with ID gets enriched",
        duration_minutes=100,
    )
    mock_registry.fetch_movie_detail.return_value = enrichment

    movie_with_id = Movie(
        id=MovieId(value="mov-id"),
        title="Movie With ID",
        description="Only movie with ID gets enriched",
        duration_minutes=100,
    )
    movie_without_id = Movie(
        id=MovieId(value="mov-no-id"),
        title="Movie Without ID",
    )

    def save_side_effect(movie: Movie) -> Movie:
        if movie.title == "Movie With ID":
            return movie_with_id
        return movie_without_id

    mock_movie_repo.save.side_effect = save_side_effect
    mock_screening_repo.save.return_value = (None, True)

    use_case = ImportScreeningsUseCase(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
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

    assert result.total_count == 2
    assert result.imported_count == 2
    mock_registry.fetch_movie_detail.assert_awaited_once_with("cinemacinema", "has-id")
    assert mock_movie_repo.save.await_count == 2

    saved_movie_with_id = mock_movie_repo.save.call_args_list[0][0][0]
    assert saved_movie_with_id.title == "Movie With ID"
    assert saved_movie_with_id.description == "Only movie with ID gets enriched"
    assert saved_movie_with_id.duration_minutes == 100
