"""Tests for FetchScreeningsFromSourceQuery."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
)
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    MovieEnrichmentData,
    ShowtimeRow,
    SourceRegistryQuery,
)
from marquise.domain.entities import (
    Cinema,
    CinemaSourceAssignment,
    SourceDefinition,
)
from marquise.domain.value_objects import CinemaId, SourceName


def _make_showtime(
    movie_title: str = "Test Movie",
    showtime: datetime | None = None,
    identifier: str | None = None,
) -> ShowtimeRow:
    return ShowtimeRow(
        movie_title=movie_title,
        showtime=showtime or datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        identifier=identifier,
        external_id=None,
        ticket_url=None,
        room=None,
        language=None,
    )


CINEMA = Cinema(id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal")
SOURCE_DEF = SourceDefinition(
    name=SourceName(value="cinemacinema"),
    display_name="Cinema Cinema",
)
ASSIGNMENT = CinemaSourceAssignment(cinema=CINEMA, source=SOURCE_DEF)


@pytest.mark.asyncio
async def test_fetch_resolves_entities_and_returns_movies_and_screenings() -> None:
    """Test that the query resolves cinema/source and returns movies and screenings."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    mock_cinema_repo.find_by_id.return_value = CINEMA
    mock_assignment_repo.find_by_cinema_id.return_value = ASSIGNMENT

    raw_rows = [
        _make_showtime("Movie A", identifier="slug-a"),
        _make_showtime("Movie B", identifier="slug-b"),
    ]
    mock_registry.fetch_showtimes.return_value = raw_rows
    mock_registry.fetch_movie_detail.side_effect = [
        MovieEnrichmentData(description="Movie A desc", duration_minutes=120),
        MovieEnrichmentData(description="Movie B desc", duration_minutes=90),
    ]

    query = FetchScreeningsFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_registry=mock_registry,
    )

    result = await query.execute(
        FetchScreeningsFromSourceQuery.InputData(
            cinema_id="cin-123",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )
    )

    assert result.cinema_id == "cin-123"
    assert result.cinema_name == "Cinéma Beaubien"
    assert result.source_name == "cinemacinema"

    assert len(result.movies) == 2
    assert len(result.screenings) == 2

    movie_a = next(m for m in result.movies if m.title == "Movie A")
    assert movie_a.identifier == "slug-a"
    assert movie_a.description == "Movie A desc"
    assert movie_a.duration_minutes == 120

    movie_b = next(m for m in result.movies if m.title == "Movie B")
    assert movie_b.identifier == "slug-b"
    assert movie_b.description == "Movie B desc"
    assert movie_b.duration_minutes == 90

    mock_registry.fetch_movie_detail.assert_any_call("cinemacinema", "slug-a")
    mock_registry.fetch_movie_detail.assert_any_call("cinemacinema", "slug-b")
    assert mock_registry.fetch_movie_detail.await_count == 2


@pytest.mark.asyncio
async def test_fetch_handles_missing_movie_detail_gracefully() -> None:
    """Test that a failed movie detail fetch doesn't block the whole import."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    mock_cinema_repo.find_by_id.return_value = CINEMA
    mock_assignment_repo.find_by_cinema_id.return_value = ASSIGNMENT

    raw_rows = [
        _make_showtime("Movie A", identifier="slug-a"),
        _make_showtime("Movie B", identifier="slug-b"),
    ]
    mock_registry.fetch_showtimes.return_value = raw_rows
    mock_registry.fetch_movie_detail.side_effect = [
        MovieEnrichmentData(description="Movie A desc"),
        RuntimeError("API error"),
    ]

    query = FetchScreeningsFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_registry=mock_registry,
    )

    result = await query.execute(
        FetchScreeningsFromSourceQuery.InputData(
            cinema_id="cin-123",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )
    )

    assert len(result.movies) == 2
    movie_a = next(m for m in result.movies if m.title == "Movie A")
    assert movie_a.description == "Movie A desc"
    movie_b = next(m for m in result.movies if m.title == "Movie B")
    assert movie_b.description is None


@pytest.mark.asyncio
async def test_fetch_dedupes_movies_by_title() -> None:
    """Test that two showtime rows with the same movie title produce one movie."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    mock_cinema_repo.find_by_id.return_value = CINEMA
    mock_assignment_repo.find_by_cinema_id.return_value = ASSIGNMENT

    raw_rows = [
        _make_showtime(
            "Movie A", datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC), identifier="slug-a"
        ),
        _make_showtime(
            "Movie B", datetime(2026, 6, 7, 20, 0, 0, tzinfo=UTC), identifier="slug-b"
        ),
        _make_showtime(
            "Movie A", datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC), identifier="slug-a"
        ),
    ]
    mock_registry.fetch_showtimes.return_value = raw_rows
    mock_registry.fetch_movie_detail.return_value = MovieEnrichmentData(
        description="Same movie"
    )

    query = FetchScreeningsFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_registry=mock_registry,
    )

    result = await query.execute(
        FetchScreeningsFromSourceQuery.InputData(
            cinema_id="cin-123",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )
    )

    # Two unique titles → two movies, but three screenings
    assert len(result.movies) == 2
    assert len(result.screenings) == 3
    mock_registry.fetch_movie_detail.assert_any_call("cinemacinema", "slug-a")
    mock_registry.fetch_movie_detail.assert_any_call("cinemacinema", "slug-b")
    assert mock_registry.fetch_movie_detail.await_count == 2


@pytest.mark.asyncio
async def test_fetch_dedupes_identifiers() -> None:
    """Test that duplicate identifiers only trigger one detail fetch."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    mock_cinema_repo.find_by_id.return_value = CINEMA
    mock_assignment_repo.find_by_cinema_id.return_value = ASSIGNMENT

    raw_rows = [
        _make_showtime("Same Movie A", identifier="shared-slug"),
        _make_showtime("Same Movie B", identifier="shared-slug"),
    ]
    mock_registry.fetch_showtimes.return_value = raw_rows
    mock_registry.fetch_movie_detail.return_value = MovieEnrichmentData(
        description="Shared detail"
    )

    query = FetchScreeningsFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_registry=mock_registry,
    )

    result = await query.execute(
        FetchScreeningsFromSourceQuery.InputData(
            cinema_id="cin-123",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )
    )

    assert len(result.movies) == 2
    assert len(result.screenings) == 2
    mock_registry.fetch_movie_detail.assert_called_once_with(
        "cinemacinema", "shared-slug"
    )


@pytest.mark.asyncio
async def test_fetch_raises_when_cinema_not_found() -> None:
    """Test that CinemaNotFoundError is raised when the cinema doesn't exist."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = None

    query = FetchScreeningsFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=create_autospec(
            CinemaSourceAssignmentRepository, instance=True
        ),
        source_registry=create_autospec(SourceRegistryQuery, instance=True),
    )

    with pytest.raises(CinemaNotFoundError, match="cin-999"):
        await query.execute(
            FetchScreeningsFromSourceQuery.InputData(
                cinema_id="cin-999",
                start_date=date(2026, 6, 7),
                end_date=date(2026, 6, 7),
            )
        )


@pytest.mark.asyncio
async def test_fetch_raises_when_no_assignment() -> None:
    """Test that CinemaSourceAssignmentNotFoundError is raised without a source."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = CINEMA
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_assignment_repo.find_by_cinema_id.return_value = None

    query = FetchScreeningsFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_registry=create_autospec(SourceRegistryQuery, instance=True),
    )

    with pytest.raises(CinemaSourceAssignmentNotFoundError):
        await query.execute(
            FetchScreeningsFromSourceQuery.InputData(
                cinema_id="cin-123",
                start_date=date(2026, 6, 7),
                end_date=date(2026, 6, 7),
            )
        )
