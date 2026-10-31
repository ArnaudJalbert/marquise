"""Import use-case dependency wiring."""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import SourceRegistryQuery
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.enrich_movie import EnrichMovieUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.match_movie import MatchMovieUseCase
from marquise.application.use_cases.merge_movies import MergeMoviesUseCase
from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase
from marquise.infrastructure.name_distance import RapidFuzzNameDistance
from marquise.infrastructure.sources.tmdb_metadata import TmdbMetadataHttpSource
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.cinema_source_assignment import (
    SupabaseCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.movie_merge import (
    SupabaseMovieMergeGateway,
)
from marquise.infrastructure.supabase.gateways.movie_metadata import (
    SupabaseMovieMetadataGateway,
)
from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)
from marquise.interface_adapters.repositories.source_adapters.tmdb_metadata import (
    TmdbMetadataAdapter,
)
from marquise.interface_adapters.repositories.supabase.cinema_repository import (
    SupabaseCinemaRepository,
)
from marquise.interface_adapters.repositories.supabase.cinema_source_assignment_repository import (  # noqa: E501
    SupabaseCinemaSourceAssignmentRepository,
)
from marquise.interface_adapters.repositories.supabase.movie_metadata_repository import (  # noqa: E501
    SupabaseMovieMetadataRepository,
)
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


def build_fetch_screenings_use_case(
    pool: asyncpg.Pool,
    schema: str,
    source_registry: SourceRegistryQuery,
) -> FetchScreeningsFromSourceQuery:
    """Build source-screening fetch query."""
    return FetchScreeningsFromSourceQuery(
        cinema_repository=SupabaseCinemaRepository(
            gateway=SupabaseCinemaGateway(pool=pool, schema=schema)
        ),
        assignment_repository=SupabaseCinemaSourceAssignmentRepository(
            gateway=SupabaseCinemaSourceAssignmentGateway(pool=pool, schema=schema)
        ),
        source_registry=source_registry,
    )


def build_create_movies_use_case(
    pool: asyncpg.Pool, schema: str, tmdb_api_key: str
) -> CreateMissingMoviesCommand:
    """Build missing-movie creation with an injected TMDB lookup."""
    movies, matcher, enricher = build_metadata_workflows(pool, schema, tmdb_api_key)
    return CreateMissingMoviesCommand(
        movie_repository=SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(pool=pool, schema=schema)
        ),
        matcher=matcher,
        enricher=enricher,
        metadata_movies=movies,
    )


def build_metadata_workflows(
    pool: asyncpg.Pool, schema: str, tmdb_api_key: str
) -> tuple[SupabaseMovieMetadataRepository, MatchMovieUseCase, EnrichMovieUseCase]:
    """Compose provider, matching and stable-ID persistence collaborators."""
    movies = SupabaseMovieMetadataRepository(
        SupabaseMovieMetadataGateway(pool, schema),
        SupabaseMovieMergeGateway(pool, schema),
    )
    metadata = TmdbMetadataAdapter(TmdbMetadataHttpSource(tmdb_api_key, max_pages=3))
    matcher = MatchMovieUseCase(metadata, RapidFuzzNameDistance())
    return (
        movies,
        matcher,
        EnrichMovieUseCase(movies, metadata, lambda: datetime.now(UTC)),
    )


def build_refresh_movies_use_case(
    pool: asyncpg.Pool, schema: str, tmdb_api_key: str
) -> RefreshMoviesUseCase:
    """Compose the explicit refresh workflow."""
    movies, _, _ = build_metadata_workflows(pool, schema, tmdb_api_key)
    metadata = TmdbMetadataAdapter(TmdbMetadataHttpSource(tmdb_api_key, max_pages=3))
    return RefreshMoviesUseCase(movies, metadata, lambda: datetime.now(UTC))


def build_merge_movies_use_case(
    pool: asyncpg.Pool, schema: str, tmdb_api_key: str
) -> MergeMoviesUseCase:
    """Compose guarded merge preview and apply."""
    movies, matcher, _ = build_metadata_workflows(pool, schema, tmdb_api_key)
    return MergeMoviesUseCase(movies, matcher)


def build_create_screenings_use_case(
    pool: asyncpg.Pool, schema: str
) -> CreateScreeningsCommand:
    """Build screening creation command."""
    return CreateScreeningsCommand(
        screening_repository=SupabaseScreeningRepository(
            gateway=SupabaseScreeningGateway(pool=pool, schema=schema)
        )
    )


def build_import_screenings_use_case(
    fetch_screenings_use_case: FetchScreeningsFromSourceQuery,
    create_movies_use_case: CreateMissingMoviesCommand,
    create_screenings_use_case: CreateScreeningsCommand,
) -> ImportScreeningsCommand:
    """Build the application-level cinema import workflow."""
    return ImportScreeningsCommand(
        fetch_screenings_use_case=fetch_screenings_use_case,
        create_movies_use_case=create_movies_use_case,
        create_screenings_use_case=create_screenings_use_case,
    )
