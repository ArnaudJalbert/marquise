"""Command use case: ensure every titled movie in a batch exists and is enriched."""

from __future__ import annotations

import asyncio
import dataclasses
from dataclasses import dataclass
from uuid import uuid4

from marquise.application.repositories import (
    MovieEnrichmentData,
    MovieRepository,
    SourceRegistryQuery,
)
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


class EnsureMoviesExistCommand:
    """Ensure a movie exists for every titled showtime row.

    Looks up movies by title in parallel, creates the missing ones, enriches
    movies that have null optional fields from the source, and saves the new or
    modified entities. Returns a mapping of normalized title to movie ID so
    callers can link screenings to their movie.
    """

    @dataclass(frozen=True, slots=True)
    class InputRow:
        """A single showtime row used for movie lookups.

        Attributes:
            movie_title: The title of the movie.
            identifier: Source-specific identifier for fetching movie details.
        """

        movie_title: str
        identifier: str | None = None

        def __post_init__(self) -> None:
            if not self.movie_title.strip():
                raise ValueError("movie_title must not be empty")

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for ensuring movies exist.

        Attributes:
            rows: The showtime rows whose movies must exist.
            source_name: The source name used for enrichment queries.
        """

        rows: tuple[EnsureMoviesExistCommand.InputRow, ...]
        source_name: str

        def __post_init__(self) -> None:
            if not self.source_name.strip():
                raise ValueError("source_name must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned by this command.

        Attributes:
            movie_lookup: Mapping of normalized movie title to movie ID (hex).
        """

        movie_lookup: dict[str, str]

    def __init__(
        self,
        movie_repository: MovieRepository,
        source_registry: SourceRegistryQuery,
    ) -> None:
        self.movie_repository = movie_repository
        self.source_registry = source_registry

    async def execute(self, request: InputData) -> OutputData:
        """Look up movies by title in parallel, creating and enriching missing ones.

        Enriches movies with metadata from the source when available. Titles
        are normalized (whitespace-collapsed) before being used as lookup or
        dict keys so that scraper noise like a trailing space doesn't create
        a duplicate movie; the repository additionally matches case-insensitively.

        Args:
            request: The showtime rows and source name.

        Returns:
            Output data with a mapping of normalized movie title to movie ID.
        """
        rows = request.rows
        source_name = request.source_name

        titles = [_normalize_title(row.movie_title) for row in rows]
        found_map = await self.movie_repository.find_by_titles(titles)

        movie_id_lookup: dict[str, str] = {}
        existing: dict[str, Movie] = {}
        missing_titles: list[str] = []
        for title in titles:
            movie = found_map[title]
            if movie is not None:
                movie_id_lookup[title] = movie.id.value
                existing[title] = movie
            else:
                missing_titles.append(title)

        # Map each unique title to its identifier for enrichment
        title_to_identifier: dict[str, str | None] = {}
        for row in rows:
            normalized_title = _normalize_title(row.movie_title)
            if normalized_title not in title_to_identifier:
                title_to_identifier[normalized_title] = row.identifier

        # -- New movies --
        new_movies_by_title: dict[str, Movie] = {}
        for title in missing_titles:
            new_movies_by_title[title] = Movie(
                id=MovieId(value=uuid4().hex),
                title=title,
            )

        # -- Build (title, identifier) pairs for movies that can be enriched --
        enrich_pairs: list[tuple[str, str]] = []
        for title in missing_titles:
            identifier = title_to_identifier.get(title)
            if identifier:
                enrich_pairs.append((title, identifier))

        for title, movie in existing.items():
            identifier = title_to_identifier.get(title)
            if identifier is not None and _needs_enrichment(movie):
                enrich_pairs.append((title, identifier))

        enriched_existing: set[str] = set()
        if enrich_pairs:
            enrich_results = await asyncio.gather(
                *[
                    self.source_registry.fetch_movie_detail(source_name, ident)
                    for _, ident in enrich_pairs
                ],
                return_exceptions=True,
            )

            for (title, _), enrichment in zip(enrich_pairs, enrich_results):
                if not isinstance(enrichment, MovieEnrichmentData):
                    continue
                if title in new_movies_by_title:
                    new_movies_by_title[title] = _apply_enrichment(
                        new_movies_by_title[title], enrichment
                    )
                else:
                    existing[title] = _apply_enrichment(existing[title], enrichment)
                    enriched_existing.add(title)

        movies_to_save_keys: list[str] = [
            *new_movies_by_title.keys(),
            *enriched_existing,
        ]
        movies_to_save: list[Movie] = [
            *new_movies_by_title.values(),
            *[existing[t] for t in enriched_existing],
        ]

        # -- Save all enriched movies in parallel --
        if movies_to_save:
            saved_movies = await asyncio.gather(
                *[self.movie_repository.save(m) for m in movies_to_save]
            )
            for key, movie in zip(movies_to_save_keys, saved_movies):
                movie_id_lookup[key] = movie.id.value
                existing[key] = movie

        return self.OutputData(movie_lookup=movie_id_lookup)


def _normalize_title(title: str) -> str:
    """Strip and collapse internal whitespace in a scraped movie title.

    Different scrapers (or the same scraper on different days) can emit the
    same title with a stray leading/trailing space or doubled internal
    spaces; normalizing keeps those from being treated as distinct movies.
    Case is left untouched — case-insensitive matching happens at the
    repository layer.
    """
    return " ".join(title.strip().split())


# Optional Movie fields that can be populated from enrichment data.
_ENRICHABLE_FIELDS = (
    "description",
    "directors",
    "cast",
    "duration_minutes",
    "release_year",
    "poster_url",
    "trailer_url",
    "genres",
    "original_title",
    "rating",
    "origin_countries",
)


def _needs_enrichment(movie: Movie) -> bool:
    """Check whether a movie has any null optional fields."""
    return any(getattr(movie, field) is None for field in _ENRICHABLE_FIELDS)


def _apply_enrichment(
    movie: Movie,
    enrichment: MovieEnrichmentData,
) -> Movie:
    """Return a new Movie with null fields populated from enrichment data."""
    updates = {
        field: getattr(enrichment, field)
        for field in _ENRICHABLE_FIELDS
        if getattr(movie, field) is None and getattr(enrichment, field) is not None
    }
    return dataclasses.replace(movie, **updates)
