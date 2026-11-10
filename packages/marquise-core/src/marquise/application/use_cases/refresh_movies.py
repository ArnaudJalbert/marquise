"""Explicitly refresh confirmed movies using the initial enrichment policy."""

from collections.abc import Callable
from datetime import datetime

from marquise.application.exceptions import (
    MetadataInvalidDataError,
    MetadataNotFoundError,
    MetadataUnavailableError,
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
        represent an unknown set. Individual retrieval/write failures are results.
        """
        if input_data.movie_id is None:
            snapshots = await self._movies.list_tmdb_movies()
        else:
            try:
                snapshot = await self._movies.get(input_data.movie_id)
            except Exception as error:
                return RefreshMoviesOutputData(
                    (
                        EnrichMovieOutputData(
                            input_data.movie_id,
                            "failed",
                            MetadataUnavailableError(str(error)),
                        ),
                    )
                )
            snapshots = (snapshot,) if snapshot is not None else ()
        results: list[EnrichMovieOutputData] = []
        if input_data.movie_id is not None and not snapshots:
            return RefreshMoviesOutputData(
                (
                    EnrichMovieOutputData(
                        input_data.movie_id,
                        "failed",
                        MetadataNotFoundError("Movie not found"),
                    ),
                )
            )
        for snapshot in sorted(snapshots, key=lambda item: item.movie_id):
            if not snapshot.tmdb_id:
                results.append(
                    EnrichMovieOutputData(
                        snapshot.movie_id,
                        "failed",
                        MetadataInvalidDataError(
                            "Movie has no confirmed TMDB identity"
                        ),
                    )
                )
                continue
            results.append(
                await _enrich(
                    EnrichMovieInputData(
                        snapshot.movie_id, ProviderIdentity("tmdb", snapshot.tmdb_id)
                    ),
                    self._movies,
                    self._metadata,
                    self._clock,
                    refresh=True,
                )
            )
        return RefreshMoviesOutputData(tuple(results))
