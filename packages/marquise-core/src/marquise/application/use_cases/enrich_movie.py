"""Select usable metadata and atomically enrich a confirmed stable movie ID."""

from collections.abc import Callable
from datetime import datetime
from urllib.parse import urlsplit

from marquise.application.metadata import (
    MetadataFailure,
    MetadataMovie,
    MetadataRepository,
)
from marquise.application.movie_workflows import (
    EnrichMovieInputData,
    EnrichMovieOutputData,
    MovieMetadataRepository,
    MovieMetadataValues,
    MovieWorkflowConflictError,
)


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
    )


async def _enrich(
    request: EnrichMovieInputData,
    movies: MovieMetadataRepository,
    metadata: MetadataRepository,
    clock: Callable[[], datetime],
    *,
    refresh: bool = False,
) -> EnrichMovieOutputData:
    try:
        snapshot = await movies.get(request.movie_id)
        if snapshot is None:
            return _failed(
                request.movie_id, MetadataFailure("not_found", "Movie not found")
            )
        if request.identity.provider != "tmdb":
            return _failed(
                request.movie_id,
                MetadataFailure(
                    "invalid_data", "Only TMDB identities can be persisted"
                ),
            )
        if snapshot.tmdb_id not in (None, request.identity.id):
            raise MovieWorkflowConflictError("Confirmed identity conflicts with movie")
        if snapshot.metadata_enriched_at is not None and not refresh:
            return EnrichMovieOutputData(request.movie_id, "unchanged")
        batch = await metadata.movie_details(request.identity)
        if batch.failure is not None:
            return _failed(request.movie_id, batch.failure)
        if not batch.complete or len(batch.items) != 1:
            return _failed(
                request.movie_id,
                MetadataFailure("invalid_data", "Expected one complete movie detail"),
            )
        movie = batch.items[0]
        if movie.identity != request.identity:
            raise ValueError("Metadata identity differs from confirmed identity")
        values = _select_values(movie)
        enriched_at = clock()
        if enriched_at.tzinfo is None or enriched_at.utcoffset() is None:
            raise ValueError("Enrichment clock must return a timezone-aware timestamp")
        await movies.update_metadata(snapshot, values, request.identity.id, enriched_at)
        return EnrichMovieOutputData(request.movie_id, "enriched")
    except (ValueError, MovieWorkflowConflictError) as error:
        return _failed(request.movie_id, MetadataFailure("invalid_data", str(error)))
    except Exception as error:
        # Repository failures must not abort cinema imports or stamp enrichment.
        return _failed(
            request.movie_id, MetadataFailure("unavailable", str(error), retryable=True)
        )


def _failed(movie_id: str, failure: MetadataFailure) -> EnrichMovieOutputData:
    return EnrichMovieOutputData(movie_id, "failed", failure)


class EnrichMovieUseCase:
    """Enrich once after identity confirmation, including legacy pending rows."""

    InputData = EnrichMovieInputData
    OutputData = EnrichMovieOutputData

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

    async def execute(self, input_data: EnrichMovieInputData) -> EnrichMovieOutputData:
        """Apply metadata once, preserving state on failed retrieval or write."""
        return await _enrich(input_data, self._movies, self._metadata, self._clock)
