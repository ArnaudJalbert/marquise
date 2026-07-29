"""Tests for FetchShowtimesFromSourceQuery."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    SourceRegistryQuery,
)
from marquise.application.use_cases.fetch_showtimes_from_source import (
    FetchShowtimesFromSourceQuery,
)
from marquise.domain.entities import (
    Cinema,
    CinemaSourceAssignment,
    SourceDefinition,
)
from marquise.domain.value_objects import CinemaId, SourceName


def _make_row(
    movie_title: str, showtime: datetime
) -> FetchShowtimesFromSourceQuery.ShowtimeDto:
    return FetchShowtimesFromSourceQuery.ShowtimeDto(
        movie_title=movie_title,
        showtime=showtime,
        identifier=None,
        external_id=None,
        ticket_url=None,
        room=None,
        language=None,
    )


@pytest.mark.asyncio
async def test_fetch_resolves_entities_and_returns_rows() -> None:
    """Test that the query resolves the cinema/source and returns raw rows."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

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

    raw_rows = [
        _make_row("Movie A", datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)),
        _make_row("Movie B", datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC)),
    ]
    mock_registry.fetch_showtimes.return_value = raw_rows

    query = FetchShowtimesFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_registry=mock_registry,
    )

    result = await query.execute(
        FetchShowtimesFromSourceQuery.InputData(
            cinema_id="cin-123",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )
    )

    assert result.cinema_id == "cin-123"
    assert result.cinema_name == "Cinéma Beaubien"
    assert result.source_name == "cinemacinema"
    assert len(result.rows) == 2
    assert result.rows[0].movie_title == "Movie A"
    assert result.rows[1].movie_title == "Movie B"

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


@pytest.mark.asyncio
async def test_fetch_raises_when_cinema_not_found() -> None:
    """Test that CinemaNotFoundError is raised when the cinema doesn't exist."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = None

    query = FetchShowtimesFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=create_autospec(
            CinemaSourceAssignmentRepository, instance=True
        ),
        source_registry=create_autospec(SourceRegistryQuery, instance=True),
    )

    with pytest.raises(CinemaNotFoundError, match="cin-999"):
        await query.execute(
            FetchShowtimesFromSourceQuery.InputData(
                cinema_id="cin-999",
                start_date=date(2026, 6, 7),
                end_date=date(2026, 6, 7),
            )
        )


@pytest.mark.asyncio
async def test_fetch_raises_when_no_assignment() -> None:
    """Test that CinemaSourceAssignmentNotFoundError is raised without a source."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_cinema_repo.find_by_id.return_value = Cinema(
        id=CinemaId(value="cin-123"), name="Cinéma Beaubien", city="Montreal"
    )
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_assignment_repo.find_by_cinema_id.return_value = None

    query = FetchShowtimesFromSourceQuery(
        cinema_repository=mock_cinema_repo,
        assignment_repository=mock_assignment_repo,
        source_registry=create_autospec(SourceRegistryQuery, instance=True),
    )

    with pytest.raises(CinemaSourceAssignmentNotFoundError):
        await query.execute(
            FetchShowtimesFromSourceQuery.InputData(
                cinema_id="cin-123",
                start_date=date(2026, 6, 7),
                end_date=date(2026, 6, 7),
            )
        )
