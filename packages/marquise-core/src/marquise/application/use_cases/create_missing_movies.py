"""Command use case: create movies that don't yet exist in the database."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from uuid import uuid4

from marquise.application.exceptions.movie import MovieIdentityConflictError
from marquise.application.metadata import ProviderIdentity
from marquise.application.movie_workflows import (
    EnrichMovieExecutor,
    EnrichMovieInputData,
    MatchMovieExecutor,
    MatchMovieInputData,
    MovieMetadataRepository,
)
from marquise.application.repositories import MovieRepository
from marquise.application.repositories.movie_identity_search import MovieIdentitySearch
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId

logger = logging.getLogger(__name__)


class CreateMissingMoviesCommand:
    """Create movies for titles not yet in the database.

    Takes movie metadata (already fetched by the caller), looks up each
    title, and persists only the missing ones.  Never updates existing
    movies.  Returns a flat list of MovieData so callers can link
    screenings to their movie.
    """

    @dataclass(frozen=True, slots=True)
    class MovieInput:
        title: str
        description: str | None = None
        directors: tuple[str, ...] | None = None
        cast: tuple[str, ...] | None = None
        duration_minutes: int | None = None
        release_year: int | None = None
        poster_url: str | None = None
        trailer_url: str | None = None
        genres: tuple[str, ...] | None = None
        original_title: str | None = None
        rating: str | None = None
        origin_countries: tuple[str, ...] | None = None
        tmdb_id: str | None = None
        identity_title: str | None = None
        source_identifier: str | None = None
        identity_titles: tuple[str, ...] = ()

        def __post_init__(self) -> None:
            if not self.title.strip():
                raise ValueError("title must not be empty")

    @dataclass(frozen=True, slots=True)
    class MovieData:
        title: str
        id: str
        source_identifier: str | None = None

        def __post_init__(self) -> None:
            if not self.title.strip():
                raise ValueError("title must not be empty")
            if not self.id.strip():
                raise ValueError("id must not be empty")

    @dataclass(frozen=True, slots=True)
    class InputData:
        movies: tuple[CreateMissingMoviesCommand.MovieInput, ...]

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movies: tuple[CreateMissingMoviesCommand.MovieData, ...]

    def __init__(
        self,
        movie_repository: MovieRepository,
        identity_search: MovieIdentitySearch | None = None,
        matcher: MatchMovieExecutor | None = None,
        enricher: EnrichMovieExecutor | None = None,
        metadata_movies: MovieMetadataRepository | None = None,
    ) -> None:
        self.movie_repository = movie_repository
        self.identity_search = identity_search
        self.matcher = matcher
        self.enricher = enricher
        self.metadata_movies = metadata_movies

    async def execute(self, input_data: InputData) -> OutputData:
        identities: dict[tuple[str, str | None], ProviderIdentity] = {}
        if self.matcher is None:
            resolved, unmatched = await self._resolve_identity(input_data.movies)
        else:
            resolved, unmatched, identities = await self._match_movies(
                input_data.movies
            )
        found_movies = await self.movie_repository.find_by_titles(
            self._search_terms(unmatched)
        )
        existing, missing = self._separate_existing(unmatched, found_movies)
        created = await self._save_missing(missing)
        movies = resolved + existing + self._created_data(unmatched, created)

        if self.enricher is not None and self.metadata_movies is not None:
            for movie in movies:
                try:
                    identity = identities.get(
                        (movie.title.casefold(), movie.source_identifier)
                    )
                    if identity is None:
                        snapshot = await self.metadata_movies.get(movie.id)
                        if snapshot and snapshot.tmdb_id:
                            identity = ProviderIdentity("tmdb", snapshot.tmdb_id)
                    if identity is not None:
                        result = await self.enricher.execute(
                            EnrichMovieInputData(movie.id, identity)
                        )
                        if result.failure:
                            logger.warning(
                                "Movie enrichment failed: %s", result.failure.kind
                            )
                except Exception as error:
                    logger.warning(
                        "Movie enrichment failed for %s: %s",
                        movie.id,
                        type(error).__name__,
                    )

        logger.info(
            "Created %d new movies, found %d existing",
            len(created),
            len(found_movies),
        )
        return self.OutputData(movies=tuple(movies))

    async def _match_movies(
        self, movies: tuple[MovieInput, ...]
    ) -> tuple[
        list[MovieData],
        tuple[MovieInput, ...],
        dict[tuple[str, str | None], ProviderIdentity],
    ]:
        """Resolve provider identities while keeping source titles for screenings."""
        assert self.matcher is not None
        resolved: list[CreateMissingMoviesCommand.MovieData] = []
        remaining: list[CreateMissingMoviesCommand.MovieInput] = []
        identities: dict[tuple[str, str | None], ProviderIdentity] = {}
        for movie in movies:
            try:
                result = await self.matcher.execute(
                    MatchMovieInputData(
                        title=movie.title,
                        release_year=movie.release_year,
                        directors=movie.directors or (),
                        duration_minutes=movie.duration_minutes,
                        identity_title=movie.identity_title,
                    )
                )
                if result.status != "matched" or result.identity is None:
                    if result.failure:
                        logger.warning(
                            "Movie identity failed for %s: %s",
                            movie.title,
                            result.failure.kind,
                        )
                    else:
                        logger.info(
                            "Movie identity %s for %s", result.status, movie.title
                        )
                    remaining.append(movie)
                    continue
                identity = result.identity
                if identity.provider != "tmdb":
                    remaining.append(movie)
                    continue
                existing = await self.movie_repository.find_by_tmdb_id(identity.id)
                identities[
                    (
                        self._normalize_title(movie.title).casefold(),
                        movie.source_identifier,
                    )
                ] = identity
                if existing is not None:
                    resolved.append(
                        self.MovieData(
                            self._normalize_title(movie.title),
                            existing.id.value,
                            movie.source_identifier,
                        )
                    )
                else:
                    remaining.append(
                        replace(
                            movie,
                            tmdb_id=identity.id,
                            release_year=movie.release_year or result.release_year,
                            identity_titles=result.titles,
                        )
                    )
            except Exception as error:
                logger.warning(
                    "Movie matching failed for %s: %s",
                    movie.title,
                    type(error).__name__,
                )
                remaining.append(movie)
        return resolved, tuple(remaining), identities

    async def _resolve_identity(
        self, movies: tuple[MovieInput, ...]
    ) -> tuple[list[MovieData], tuple[MovieInput, ...]]:
        """Reuse known movie identities before trying the old title lookup."""
        if self.identity_search is None:
            return [], movies
        resolved: list[CreateMissingMoviesCommand.MovieData] = []
        remaining: list[CreateMissingMoviesCommand.MovieInput] = []
        for movie in movies:
            candidates = await self.identity_search.search(
                movie.identity_title or movie.title, movie.release_year
            )
            if len(candidates) != 1 or candidates[0].provider != "tmdb":
                remaining.append(movie)
                continue
            tmdb_id = candidates[0].id
            existing = await self.movie_repository.find_by_tmdb_id(tmdb_id)
            if existing is not None:
                resolved.append(
                    self.MovieData(
                        self._normalize_title(movie.title),
                        existing.id.value,
                        movie.source_identifier,
                    )
                )
            else:
                remaining.append(replace(movie, tmdb_id=tmdb_id))
        return resolved, tuple(remaining)

    @staticmethod
    def _search_terms(movies: tuple[MovieInput, ...]) -> list[str]:
        """Choose one broad database search term per canonical title."""
        return list(
            dict.fromkeys(
                max(key.split(), key=len)
                for movie in movies
                for title in (movie.title, *movie.identity_titles)
                if (key := Movie.title_key(title))
            )
        )

    @classmethod
    def _separate_existing(
        cls,
        movie_inputs: tuple[MovieInput, ...],
        found_movies: list[Movie],
    ) -> tuple[list[MovieData], dict[str, MovieInput]]:
        """Return existing movies and one pending input per known identity."""
        existing: list[CreateMissingMoviesCommand.MovieData] = []
        missing: dict[str, CreateMissingMoviesCommand.MovieInput] = {}
        aliases = cls._identity_aliases(movie_inputs)

        for movie_input in movie_inputs:
            title = cls._normalize_title(movie_input.title)
            titles = (title, *movie_input.identity_titles)
            candidates = found_movies
            if movie_input.tmdb_id is not None:
                candidates = [
                    movie
                    for movie in found_movies
                    if movie.tmdb_id in {None, movie_input.tmdb_id}
                ]
                if any(
                    movie.tmdb_id not in {None, movie_input.tmdb_id}
                    and Movie.search_title(movie.title).casefold()
                    == Movie.search_title(title).casefold()
                    for movie in found_movies
                ):
                    # Another film owns this title, e.g. a remake. Keep both.
                    if movie_input.release_year is None:
                        raise MovieIdentityConflictError(
                            f"Movie '{title}' already has a different TMDB id"
                        )
                    title = f"{title} ({movie_input.release_year})"
                    movie_input = replace(movie_input, title=title)
            movie = cls._find_match(
                candidates,
                titles=titles,
                release_year=movie_input.release_year,
            )
            if movie is not None:
                existing.append(
                    cls.MovieData(
                        title=title,
                        id=movie.id.value,
                        source_identifier=movie_input.source_identifier,
                    )
                )
            else:
                key = cls._movie_key(movie_input, aliases)
                if key.startswith("tmdb:") or key not in missing:
                    missing[key] = (
                        movie_input
                        if key not in missing or movie_input.tmdb_id
                        else missing[key]
                    )
        return existing, missing

    @staticmethod
    def _identity_aliases(movie_inputs: tuple[MovieInput, ...]) -> dict[str, str]:
        """Map title keys to the batch's single matched identity for that title.

        Label variants such as ``Fjord (VOSTA)`` then share the matched row
        instead of creating an unmatched twin in the same import.
        """
        owners: dict[str, set[str]] = {}
        for movie in movie_inputs:
            if movie.tmdb_id is not None:
                for title in (movie.title, *movie.identity_titles):
                    if key := Movie.title_key(title):
                        owners.setdefault(key, set()).add(movie.tmdb_id)
        return {
            key: f"tmdb:{next(iter(ids))}"
            for key, ids in owners.items()
            if len(ids) == 1
        }

    async def _save_missing(self, missing: dict[str, MovieInput]) -> dict[str, Movie]:
        """Create or reuse each distinct film without updating existing details."""
        saved = await asyncio.gather(
            *(
                self.movie_repository.create_or_reuse(self._movie(movie))
                for movie in missing.values()
            )
        )
        return dict(zip(missing, saved, strict=True))

    @staticmethod
    def _movie_key(movie: MovieInput, aliases: dict[str, str] | None = None) -> str:
        """Prefer a known identity; title grouping is only a fallback."""
        if movie.tmdb_id is not None:
            return f"tmdb:{movie.tmdb_id}"
        key = Movie.title_key(movie.title)
        return (aliases or {}).get(key, f"title:{key}")

    @classmethod
    def _created_data(
        cls,
        movie_inputs: tuple[MovieInput, ...],
        created: dict[str, Movie],
    ) -> list[MovieData]:
        """Build output rows for every input represented by a created movie."""
        aliases = cls._identity_aliases(movie_inputs)
        return [
            cls.MovieData(
                title=cls._normalize_title(movie_input.title),
                id=movie.id.value,
                source_identifier=movie_input.source_identifier,
            )
            for movie_input in movie_inputs
            if (movie := created.get(cls._movie_key(movie_input, aliases))) is not None
        ]

    @staticmethod
    def _movie(movie_input: MovieInput) -> Movie:
        """Build a new movie entity from one scraped input."""
        return Movie(
            id=MovieId(value=uuid4().hex),
            title=CreateMissingMoviesCommand._normalize_title(movie_input.title),
            description=movie_input.description,
            directors=movie_input.directors,
            cast=movie_input.cast,
            duration_minutes=movie_input.duration_minutes,
            release_year=movie_input.release_year,
            poster_url=movie_input.poster_url,
            trailer_url=movie_input.trailer_url,
            genres=movie_input.genres,
            original_title=movie_input.original_title,
            rating=movie_input.rating,
            origin_countries=movie_input.origin_countries,
            tmdb_id=movie_input.tmdb_id,
        )

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Strip and collapse internal whitespace in a scraped movie title."""
        return " ".join(title.strip().split())

    @classmethod
    def _find_match(
        cls,
        candidates: list[Movie],
        *,
        titles: tuple[str, ...],
        release_year: int | None,
    ) -> Movie | None:
        """Return the one compatible candidate by title key, then containment.

        Comparison ignores case, accents, punctuation and screening labels.
        Ambiguous candidates return None so a new movie is created instead.
        """
        compatible = [
            movie
            for movie in candidates
            if release_year is None
            or movie.release_year is None
            or movie.release_year == release_year
        ]
        keys = {key for title in titles if (key := Movie.title_key(title))}
        same = [movie for movie in compatible if Movie.title_key(movie.title) in keys]
        if len(same) > 1:
            exact = [
                movie
                for movie in same
                if any(
                    cls._normalize_title(movie.title).casefold()
                    == cls._normalize_title(title).casefold()
                    for title in titles
                )
            ]
            same = exact if len(exact) == 1 else same
        if same:
            return same[0] if len(same) == 1 else None
        overlapping = [
            movie
            for movie in compatible
            if any(Movie.titles_overlap(movie.title, title) for title in titles)
        ]
        return overlapping[0] if len(overlapping) == 1 else None
