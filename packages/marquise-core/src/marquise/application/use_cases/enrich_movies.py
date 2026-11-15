"""Select usable metadata and atomically enrich confirmed stable movie IDs."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from urllib.parse import urlsplit

from marquise.application.exceptions import (
    MetadataInvalidDataError,
    MetadataNotFoundError,
)
from marquise.application.metadata import (
    MetadataMovie,
    MetadataRepository,
    ProviderIdentity,
)
from marquise.application.movie_workflows import (
    EnrichMovieInputData,
    EnrichMovieOutputData,
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    MovieWorkflowConflictError,
)

logger = logging.getLogger(__name__)


def _text(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


def _url(value: str | None) -> str | None:
    value = _text(value)
    if value is None:
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme in {"https", "http"}
            and parsed.hostname
            and not any(char.isspace() for char in value)
            and (parsed.port is None or parsed.port > 0)
        ):
            return value
    except ValueError:
        pass
    return None


def _names(values: tuple[str, ...]) -> tuple[str, ...] | None:
    return tuple(name for value in values if (name := _text(value))) or None


def _positive(value: int | None) -> int | None:
    return value if type(value) is int and value > 0 else None


def _select_values(movie: MetadataMovie) -> MovieMetadataValues:
    # English-first for now; French titles are deliberately not selected.
    localized = [
        item
        for locale in ("en-US", "fr-CA")
        for item in movie.localized
        if item.locale == locale
    ]
    english_titles = [
        fact.title
        for fact in movie.titles
        if fact.kind == "canonical" and fact.locale == "en-US"
    ] + [item.title for item in localized if item.locale == "en-US"]
    return MovieMetadataValues(
        title=next((_text(title) for title in english_titles if _text(title)), None),
        description=next(
            (_text(item.synopsis) for item in localized if _text(item.synopsis)), None
        ),
        poster_url=next(
            (
                _url(item.poster_url)
                for locale in ("en-US", "en", "und", "fr-CA", "fr")
                for item in movie.localized
                if item.locale == locale and _url(item.poster_url)
            ),
            None,
        ),
        original_title=_text(movie.original_title),
        release_year=_positive(movie.release_year),
        duration_minutes=_positive(movie.duration_minutes),
        directors=_names(tuple(person.name for person in movie.directors)),
        cast=_names(tuple(person.name for person in movie.cast)),
        genres=_names(movie.genres),
        origin_countries=_names(movie.origin_countries),
        trailer_url=next(
            (
                _url(media.url)
                for language in ("en", "fr")
                for media in movie.media
                if media.language == language
                and media.official
                and media.kind == "trailer"
                and _url(media.url)
            ),
            None,
        ),
        rating=next(
            (
                _text(item.rating)
                for item in movie.certifications
                if item.country == "CA" and _text(item.rating)
            ),
            None,
        ),
        tmdb_rating=movie.tmdb_rating,
        tmdb_vote_count=movie.tmdb_vote_count,
    )


async def _enrich(
    request: EnrichMovieInputData,
    movies: MovieMetadataRepository,
    metadata: MetadataRepository,
    clock: Callable[[], datetime],
    *,
    refresh: bool = False,
) -> EnrichMovieOutputData:
    snapshot = await movies.get(request.movie_id)
    if snapshot is None:
        return _not_enriched(request.movie_id, MetadataNotFoundError("Movie not found"))
    if request.identity.provider != "tmdb":
        return _not_enriched(
            request.movie_id,
            MetadataInvalidDataError("Only TMDB identities can be persisted"),
        )
    if snapshot.tmdb_id not in (None, request.identity.id):
        raise MovieWorkflowConflictError("Confirmed identity conflicts with movie")
    if (
        snapshot.metadata_enriched_at is not None
        and snapshot.values.tmdb_vote_count is not None
        and not refresh
    ):
        return EnrichMovieOutputData(request.movie_id, "unchanged")
    batch = await metadata.movie_details(request.identity)
    if batch.failure is not None:
        raise batch.failure
    if not batch.complete or len(batch.items) != 1:
        return _not_enriched(
            request.movie_id,
            MetadataInvalidDataError("Expected one complete movie detail"),
        )
    movie = batch.items[0]
    if movie.identity != request.identity:
        return _not_enriched(
            request.movie_id,
            MetadataInvalidDataError(
                "Metadata identity differs from confirmed identity"
            ),
        )
    values = _select_values(movie)
    enriched_at = clock()
    if enriched_at.tzinfo is None or enriched_at.utcoffset() is None:
        raise ValueError("Enrichment clock must return a timezone-aware timestamp")
    try:
        await movies.update_metadata(snapshot, values, request.identity.id, enriched_at)
    except MovieWorkflowConflictError:
        retry = _to_year_titled_values(request.movie_id, snapshot, values)
        if retry is None:
            raise
        await movies.update_metadata(snapshot, retry, request.identity.id, enriched_at)
    return EnrichMovieOutputData(request.movie_id, "enriched")


def _to_year_titled_values(
    movie_id: str, snapshot: MovieMetadataSnapshot, values: MovieMetadataValues
) -> MovieMetadataValues | None:
    """Return values titled with the release year, or None without title or year.

    Another film can own the title, e.g. a remake, so the year disambiguates it.
    """
    year = values.release_year or snapshot.values.release_year
    if values.title is None or year is None:
        return None
    title = f"{values.title} ({year})"
    logger.warning("Movie %s title %r taken; retry %r", movie_id, values.title, title)
    return replace(values, title=title)


def _not_enriched(movie_id: str, failure: Exception) -> EnrichMovieOutputData:
    """Log an expected miss and leave the movie not enriched."""
    logger.warning("Movie %s not enriched: %s", movie_id, type(failure).__name__)
    return EnrichMovieOutputData(movie_id, "not_enriched", failure)


class EnrichMoviesUseCase:
    """Enrich movies once after identity confirmation, one at a time."""

    @dataclass(frozen=True, slots=True)
    class MovieInput:
        """A stored movie, with its TMDB ID when matching just confirmed one."""

        movie_id: str
        tmdb_id: str | None = None

        def __post_init__(self) -> None:
            if not isinstance(self.movie_id, str):
                raise TypeError("movie_id must be a string")
            if self.tmdb_id is not None and not isinstance(self.tmdb_id, str):
                raise TypeError("tmdb_id must be a string")

    @dataclass(frozen=True, slots=True)
    class InputData:
        movies: tuple[EnrichMoviesUseCase.MovieInput, ...]

        def __post_init__(self) -> None:
            if not isinstance(self.movies, tuple):
                raise TypeError("movies must be a tuple")
            for movie in self.movies:
                if not isinstance(movie, EnrichMoviesUseCase.MovieInput):
                    raise TypeError("movies must only contain MovieInput")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        enriched_ids: tuple[str, ...]
        not_enriched_ids: tuple[str, ...]

    def __init__(
        self,
        movie_repository: MovieMetadataRepository,
        metadata_repository: MetadataRepository,
        clock: Callable[[], datetime],
    ) -> None:
        """Inject persistence, provider facts and the successful-write clock."""
        self._movies = movie_repository
        self._metadata = metadata_repository
        self._clock = clock

    async def execute(self, input_data: InputData) -> OutputData:
        """Enrich every movie with a known identity.

        Unexpected dependency errors propagate and stop enrichment.

        Args:
            input_data: The movies to enrich.

        Returns:
            The IDs enriched, and the IDs skipped for missing or invalid metadata.
            A movie with no known identity is in neither.

        Raises:
            MetadataFailure: If metadata retrieval fails for any reason other
                than missing or invalid data.
            MovieWorkflowConflictError: If the stored identity conflicts, or a
                title write conflict cannot be resolved by appending the
                release year.
            ValueError: If the clock returns a timestamp without a timezone.
        """
        results = [
            await self._enrich_one(movie.movie_id, movie.tmdb_id)
            for movie in input_data.movies
        ]
        logger.info("Enrichment finished for %d movies", len(results))
        return self._build_output(results)

    async def _enrich_one(
        self, movie_id: str, tmdb_id: str | None
    ) -> EnrichMovieOutputData:
        """Enrich one movie, skipping only missing or invalid metadata."""
        try:
            return await self._enrich_known(movie_id, tmdb_id)
        except (MetadataNotFoundError, MetadataInvalidDataError) as error:
            return _not_enriched(movie_id, error)

    async def _enrich_known(
        self, movie_id: str, tmdb_id: str | None
    ) -> EnrichMovieOutputData:
        """Enrich one movie. A movie with no known identity is left as it is."""
        known_tmdb_id = await self._find_known_tmdb_id(movie_id, tmdb_id)
        if known_tmdb_id is None:
            return EnrichMovieOutputData(movie_id, "unchanged")
        request = EnrichMovieInputData(
            movie_id, ProviderIdentity("tmdb", known_tmdb_id)
        )
        return await _enrich(request, self._movies, self._metadata, self._clock)

    async def _find_known_tmdb_id(
        self, movie_id: str, tmdb_id: str | None
    ) -> str | None:
        """Return the identity from matching, or the one already stored."""
        if tmdb_id is not None:
            return tmdb_id
        snapshot = await self._movies.get(movie_id)
        return None if snapshot is None else snapshot.tmdb_id

    @staticmethod
    def _build_output(results: list[EnrichMovieOutputData]) -> OutputData:
        """Keep the IDs that were enriched and the IDs left not enriched."""
        return EnrichMoviesUseCase.OutputData(
            enriched_ids=tuple(
                result.movie_id for result in results if result.status == "enriched"
            ),
            not_enriched_ids=tuple(
                result.movie_id for result in results if result.status == "not_enriched"
            ),
        )
