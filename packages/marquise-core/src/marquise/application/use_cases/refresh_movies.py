"""Explicitly refresh confirmed movies using the initial enrichment policy."""

import logging
from collections.abc import Callable
from datetime import datetime

from marquise.application.exceptions import (
    MetadataInvalidDataError,
    MetadataNotFoundError,
)
from marquise.application.metadata import MetadataRepository, ProviderIdentity
from marquise.application.movie_workflows import (
    EnrichMovieInputData,
    EnrichMovieOutputData,
    MovieMetadataRepository,
    RefreshMoviesInputData,
    RefreshMoviesOutputData,
)
from marquise.application.use_cases.enrich_movies import _enrich

logger = logging.getLogger(__name__)


class RefreshMoviesUseCase:
    """Refresh one or all TMDB-linked movies in stable movie-ID order."""

    InputData = RefreshMoviesInputData
    OutputData = RefreshMoviesOutputData

    def __init__(
        self,
        movie_repository: MovieMetadataRepository,
        metadata_repository: MetadataRepository,
        clock: Callable[[], datetime],
    ) -> None:
        """Inject the same collaborators used for initial enrichment."""
        self._movies = movie_repository
        self._metadata = metadata_repository
        self._clock = clock

    async def execute(
        self, input_data: RefreshMoviesInputData
    ) -> RefreshMoviesOutputData:
        """Refresh confirmed identities and report each movie's outcome.

        Failure to enumerate movies propagates, since no per-movie result can
        represent an unknown set. Any failure or internal error for one movie
        leaves it not enriched and is listed, so it never stops the refresh.
        """
        if input_data.movie_id is None:
            snapshots = await self._movies.list_tmdb_movies()
        else:
            snapshot = await self._movies.get(input_data.movie_id)
            snapshots = (snapshot,) if snapshot is not None else ()
        results: list[EnrichMovieOutputData] = []
        if input_data.movie_id is not None and not snapshots:
            return RefreshMoviesOutputData(
                (
                    self._not_enriched(
                        input_data.movie_id, MetadataNotFoundError("Movie not found")
                    ),
                )
            )
        for snapshot in sorted(snapshots, key=lambda item: item.movie_id):
            if not snapshot.tmdb_id:
                results.append(
                    self._not_enriched(
                        snapshot.movie_id,
                        MetadataInvalidDataError(
                            "Movie has no confirmed TMDB identity"
                        ),
                    )
                )
                continue
            try:
                result = await _enrich(
                    EnrichMovieInputData(
                        snapshot.movie_id, ProviderIdentity("tmdb", snapshot.tmdb_id)
                    ),
                    self._movies,
                    self._metadata,
                    self._clock,
                    refresh=True,
                )
            except Exception as error:
                result = self._not_enriched(snapshot.movie_id, error)
            results.append(result)
        return RefreshMoviesOutputData(tuple(results))

    @staticmethod
    def _not_enriched(movie_id: str, failure: Exception) -> EnrichMovieOutputData:
        """List one movie as not enriched; it never stops the refresh."""
        logger.warning("Movie %s not enriched: %s", movie_id, type(failure).__name__)
        return EnrichMovieOutputData(movie_id, "not_enriched", failure)
