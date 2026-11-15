"""A metadata outage during enrichment fails the import after screenings are saved."""

from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import MetadataUnavailableError
from marquise.application.metadata import MetadataBatch, MetadataRepository
from marquise.application.movie_workflows import (
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
)
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
from support.movie_import import (
    DAY,
    autospec_use_case,
    build_match,
    build_matcher,
    import_command,
)


@pytest.mark.asyncio
async def test_enrichment_outage_propagates_after_screenings_are_saved() -> None:
    """A TMDB outage while enriching fails the import once screenings are saved."""
    fetch = autospec_use_case(FetchScreeningsFromSourceQuery)
    fetch.execute.return_value = FetchScreeningsFromSourceQuery.OutputData(
        "cinema",
        "Cinema",
        "source",
        (FetchScreeningsFromSourceQuery.FetchedMovieData(title="Film"),),
        (FetchScreeningsFromSourceQuery.FetchedScreeningData("Film", DAY),),
    )
    movies = create_autospec(MovieRepository, instance=True)
    movies.find_by_tmdb_id.return_value = None
    movies.find_by_titles.return_value = []
    movies.create_or_reuse.side_effect = lambda movie: movie
    create_screenings = autospec_use_case(CreateScreeningsCommand)
    create_screenings.execute.return_value = CreateScreeningsCommand.OutputData(
        (), 1, 0, 0, 0
    )
    provider = create_autospec(MetadataRepository, instance=True)
    provider.movie_details.return_value = MetadataBatch(
        (), complete=False, failure=MetadataUnavailableError("provider down")
    )
    metadata_movies = create_autospec(MovieMetadataRepository, instance=True)
    metadata_movies.get.side_effect = lambda movie_id: MovieMetadataSnapshot(
        movie_id, "1", MovieMetadataValues(title="Film"), tmdb_id="1"
    )
    enricher = EnrichMoviesUseCase(
        metadata_movies, provider, lambda: datetime(2026, 10, 31, tzinfo=UTC)
    )
    command = import_command(
        fetch, movies, create_screenings, build_matcher(build_match("1")), enricher
    )
    with pytest.raises(MetadataUnavailableError, match="provider down"):
        await command.execute(
            command.InputData("cinema", date(2026, 10, 31), DAY.date())
        )
    create_screenings.execute.assert_awaited_once()
    metadata_movies.update_metadata.assert_not_awaited()
