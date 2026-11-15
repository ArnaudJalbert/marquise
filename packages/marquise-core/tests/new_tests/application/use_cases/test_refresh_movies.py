"""Refresh reports and logs provider outages without stopping the batch."""

import logging
from datetime import UTC, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions import MetadataUnavailableError
from marquise.application.metadata import MetadataBatch, MetadataRepository
from marquise.application.movie_workflows import (
    EnrichMovieOutputData,
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
)
from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase


@pytest.fixture
def provider() -> Mock:
    """A metadata outage returned as a failed batch."""
    provider = create_autospec(MetadataRepository, instance=True)
    provider.movie_details.return_value = MetadataBatch(
        (), complete=False, failure=MetadataUnavailableError("provider down")
    )
    return provider


@pytest.fixture
def use_case(provider: Mock) -> RefreshMoviesUseCase:
    """Refresh a confirmed Movie through autospecced repository ports."""
    movies = create_autospec(MovieMetadataRepository, instance=True)
    movies.get.return_value = MovieMetadataSnapshot(
        "one", "1", MovieMetadataValues(title="Film"), "7"
    )
    return RefreshMoviesUseCase(
        movies, provider, lambda: datetime(2026, 10, 31, tzinfo=UTC)
    )


@pytest.mark.asyncio
async def test_failed_batch_is_reported_and_logged(
    use_case: RefreshMoviesUseCase, provider: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed metadata batch leaves a visible warning and not-enriched result."""
    with caplog.at_level(logging.WARNING):
        output = await use_case.execute(use_case.InputData("one"))
    assert output.results == (
        EnrichMovieOutputData(
            "one", "not_enriched", provider.movie_details.return_value.failure
        ),
    )
    assert "Movie one not enriched: MetadataUnavailableError" in caplog.messages
