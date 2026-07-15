"""Tests for SourceRegistry.fetch_showtimes."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.repositories.source_registry_query import ShowtimeRow
from marquise.domain.entities import Cinema, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName
from marquise.interface_adapters.repositories.source_adapters.base import (
    SourceAdapter,
)
from marquise.interface_adapters.repositories.source_registry import SourceRegistry


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide a sample Cinema for tests."""
    return Cinema(
        id=CinemaId(value="cin-123"),
        name="Cinéma Beaubien",
        city="Montreal",
    )


@pytest.fixture
def sample_source_definition() -> SourceDefinition:
    """Provide a sample SourceDefinition for tests."""
    return SourceDefinition(
        name=SourceName(value="test_source"),
        display_name="Test Source",
    )


@pytest.mark.asyncio
async def test_fetch_showtimes_adapts_dicts_to_showtime_rows(
    sample_cinema: Cinema,
    sample_source_definition: SourceDefinition,
) -> None:
    """Test fetch_showtimes maps raw dicts to ShowtimeRow dataclasses."""
    registry = SourceRegistry()
    mock_adapter = create_autospec(SourceAdapter, instance=True)
    mock_adapter.fetch_showtimes.return_value = [
        {
            "movie_title": "Movie A",
            "showtime": "2026-06-07T19:30:00",
        },
        {
            "movie_title": "Movie B",
            "showtime": "2026-06-07T21:00:00",
        },
    ]

    registry.register("test_source", mock_adapter)

    results = await registry.fetch_showtimes(
        cinema=sample_cinema,
        source_definition=sample_source_definition,
        start_date=datetime(2026, 6, 7, tzinfo=UTC),
        end_date=datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC),
    )

    assert len(results) == 2

    assert isinstance(results[0], ShowtimeRow)
    assert results[0].movie_title == "Movie A"
    assert results[0].showtime == datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)

    assert results[1].movie_title == "Movie B"

    mock_adapter.fetch_showtimes.assert_awaited_once_with(
        cinema=sample_cinema,
        start_date=datetime(2026, 6, 7, tzinfo=UTC),
        end_date=datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_fetch_showtimes_handles_empty_result(
    sample_source_definition: SourceDefinition,
) -> None:
    """Test fetch_showtimes returns empty list when adapter returns empty."""
    registry = SourceRegistry()
    mock_adapter = create_autospec(SourceAdapter, instance=True)
    mock_adapter.fetch_showtimes.return_value = []

    registry.register("test_source", mock_adapter)

    results = await registry.fetch_showtimes(
        cinema=sample_cinema,
        source_definition=sample_source_definition,
        start_date=datetime(2026, 6, 7, tzinfo=UTC),
        end_date=datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC),
    )

    assert results == []


@pytest.mark.asyncio
async def test_fetch_showtimes_raises_key_error_for_unknown_source(
    sample_cinema: Cinema,
) -> None:
    """Test fetch_showtimes raises KeyError for unknown source."""
    registry = SourceRegistry()
    unknown = SourceDefinition(
        name=SourceName(value="unknown"),
        display_name="Unknown",
    )

    with pytest.raises(KeyError, match="unknown"):
        await registry.fetch_showtimes(
            cinema=sample_cinema,
            source_definition=unknown,
            start_date=datetime(2026, 6, 7, tzinfo=UTC),
            end_date=datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_fetch_showtimes_skips_rows_without_showtime(
    sample_cinema: Cinema,
    sample_source_definition: SourceDefinition,
) -> None:
    """Test fetch_showtimes skips rows that have no showtime key."""
    registry = SourceRegistry()
    mock_adapter = create_autospec(SourceAdapter, instance=True)
    mock_adapter.fetch_showtimes.return_value = [
        {"movie_title": "Only Title"},
    ]

    registry.register("test_source", mock_adapter)

    results = await registry.fetch_showtimes(
        cinema=sample_cinema,
        source_definition=sample_source_definition,
        start_date=datetime(2026, 6, 7, tzinfo=UTC),
        end_date=datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC),
    )

    assert results == []
