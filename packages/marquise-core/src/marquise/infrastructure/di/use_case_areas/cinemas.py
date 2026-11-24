"""Wired cinema use cases and queries."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.di.queries import build_get_cinema_screenings_query
from marquise.infrastructure.postgres.config.settings import Settings
from marquise.infrastructure.postgres.gateways.cinema import PostgresCinemaGateway
from marquise.infrastructure.postgres.gateways.screening import (
    PostgresScreeningGateway,
)
from marquise.interface_adapters.repositories.cinema_repository import (
    PostgresCinemaRepository,
)
from marquise.interface_adapters.repositories.screening_repository import (
    PostgresScreeningRepository,
)


@dataclass(frozen=True, slots=True)
class CinemaUseCases:
    """Wired use cases and queries that read and change cinemas."""

    create_cinema_use_case: CreateCinemaUseCase
    delete_cinema_use_case: DeleteCinemaUseCase
    update_cinema_use_case: UpdateCinemaUseCase
    list_cinemas_use_case: ListCinemasUseCase
    get_cinema_use_case: GetCinemaUseCase
    get_cinema_movies_use_case: GetCinemaMoviesUseCase
    get_cinema_screenings_query: GetCinemaScreeningsQuery


def build_cinema_repository(
    pool: asyncpg.Pool, schema: str
) -> PostgresCinemaRepository:
    """Build the cinema repository over its Postgres gateway."""
    return PostgresCinemaRepository(
        gateway=PostgresCinemaGateway(pool=pool, schema=schema)
    )


def build_cinema_use_cases(pool: asyncpg.Pool, settings: Settings) -> CinemaUseCases:
    """Wire every cinema use case and query.

    Args:
        pool: Open connection pool shared by every gateway.
        settings: Settings that name the database schema.

    Returns:
        The cinema use cases, all sharing one cinema repository.
    """
    cinema_repository = build_cinema_repository(pool, settings.schema)
    return CinemaUseCases(
        create_cinema_use_case=CreateCinemaUseCase(cinema_repository=cinema_repository),
        delete_cinema_use_case=DeleteCinemaUseCase(cinema_repository=cinema_repository),
        update_cinema_use_case=UpdateCinemaUseCase(cinema_repository=cinema_repository),
        list_cinemas_use_case=ListCinemasUseCase(cinema_repository=cinema_repository),
        get_cinema_use_case=GetCinemaUseCase(cinema_repository=cinema_repository),
        get_cinema_movies_use_case=GetCinemaMoviesUseCase(
            cinema_repository=cinema_repository,
            screening_repository=PostgresScreeningRepository(
                gateway=PostgresScreeningGateway(pool=pool, schema=settings.schema)
            ),
        ),
        get_cinema_screenings_query=build_get_cinema_screenings_query(
            pool, settings.schema
        ),
    )
