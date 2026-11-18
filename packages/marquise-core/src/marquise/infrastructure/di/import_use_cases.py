"""Import use-case dependency wiring."""

from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
from marquise.application.queries.link_screenings import LinkScreeningsQuery
from marquise.application.repositories import SourceRegistryQuery
from marquise.application.use_cases.create_movies import CreateMoviesCommand
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.match_movies import MatchMoviesUseCase
from marquise.application.use_cases.merge_movies import MergeMoviesUseCase
from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase
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


def build_find_stored_movies_query(
    pool: asyncpg.Pool, schema: str
) -> FindStoredMoviesQuery:
    """Build the stored movie lookup."""
    return FindStoredMoviesQuery(
        movie_repository=SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(pool=pool, schema=schema)
        )
    )


def build_create_movies_use_case(
    pool: asyncpg.Pool, schema: str
) -> CreateMoviesCommand:
    """Build movie creation."""
    return CreateMoviesCommand(
        movie_repository=SupabaseMovieRepository(
            gateway=SupabaseMovieGateway(pool=pool, schema=schema)
        )
    )


def _build_movie_metadata_repository(
    pool: asyncpg.Pool, schema: str
) -> SupabaseMovieMetadataRepository:
    """Build stable-ID movie persistence with its merge gateway."""
    return SupabaseMovieMetadataRepository(
        SupabaseMovieMetadataGateway(pool, schema),
        SupabaseMovieMergeGateway(pool, schema),
    )


def _build_tmdb_metadata(tmdb_api_key: str) -> TmdbMetadataAdapter:
    """Build the TMDB metadata provider."""
    return TmdbMetadataAdapter(TmdbMetadataHttpSource(tmdb_api_key))


def _build_movie_matcher(metadata: TmdbMetadataAdapter) -> MatchMoviesUseCase:
    """Build provider matching."""
    return MatchMoviesUseCase(metadata)


def build_refresh_movies_use_case(
    pool: asyncpg.Pool, schema: str, tmdb_api_key: str
) -> RefreshMoviesUseCase:
    """Compose the explicit refresh workflow."""
    return RefreshMoviesUseCase(
        _build_movie_metadata_repository(pool, schema),
        _build_tmdb_metadata(tmdb_api_key),
        lambda: datetime.now(UTC),
    )


def build_merge_movies_use_case(
    pool: asyncpg.Pool, schema: str, tmdb_api_key: str
) -> MergeMoviesUseCase:
    """Compose guarded merge preview and apply."""
    return MergeMoviesUseCase(
        _build_movie_metadata_repository(pool, schema),
        _build_movie_matcher(_build_tmdb_metadata(tmdb_api_key)),
    )


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
    pool: asyncpg.Pool,
    schema: str,
    tmdb_api_key: str,
    fetch_screenings_use_case: FetchScreeningsFromSourceQuery,
) -> ImportScreeningsCommand:
    """Build the application-level cinema import workflow."""
    metadata = _build_tmdb_metadata(tmdb_api_key)
    return ImportScreeningsCommand(
        fetch_screenings=fetch_screenings_use_case,
        match_movies=_build_movie_matcher(metadata),
        find_stored_movies=build_find_stored_movies_query(pool, schema),
        create_movies=build_create_movies_use_case(pool, schema),
        link_screenings=LinkScreeningsQuery(),
        create_screenings=build_create_screenings_use_case(pool, schema),
        enrich_movies=EnrichMoviesUseCase(
            _build_movie_metadata_repository(pool, schema),
            metadata,
            lambda: datetime.now(UTC),
        ),
    )
