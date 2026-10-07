"""Composition root for connection-scoped audited screening writes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import asyncpg

from marquise.application.transactions.screening_write import ScreeningWriteSession
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.application.use_cases.write_screening import WriteScreeningUseCase
from marquise.infrastructure.supabase.connection_pool import ConnectionPool
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import SupabaseScreeningGateway
from marquise.infrastructure.supabase.gateways.screening_write import (
    SupabaseScreeningWriteGateway,
)
from marquise.infrastructure.supabase.screening_write_transaction import (
    SupabaseScreeningWriteTransaction,
)
from marquise.interface_adapters.repositories.screening_write import (
    ScreeningWriteSessionAdapter,
)
from marquise.interface_adapters.repositories.supabase.cinema_repository import (
    SupabaseCinemaRepository,
)
from marquise.interface_adapters.repositories.supabase.movie_repository import (
    SupabaseMovieRepository,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


class _TransactionPool:
    """Reuse existing gateways on one active connection without reacquiring it."""

    def __init__(self, connection: asyncpg.Connection) -> None:
        self._connection = connection

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        yield self._connection


def build_write_screening_use_case(
    pool: ConnectionPool, schema: str
) -> WriteScreeningUseCase:
    """Inject the transaction, connection-scoped collaborators, clock, and IDs."""

    def build_session(
        connection: asyncpg.Connection, account: str, key: str
    ) -> ScreeningWriteSession:
        bound_pool = _TransactionPool(connection)
        screenings = SupabaseScreeningRepository(
            SupabaseScreeningGateway(bound_pool, schema)
        )
        movies = SupabaseMovieRepository(SupabaseMovieGateway(bound_pool, schema))
        cinemas = SupabaseCinemaRepository(SupabaseCinemaGateway(bound_pool, schema))
        return ScreeningWriteSessionAdapter(
            SupabaseScreeningWriteGateway(connection, account, key, schema),
            create=CreateScreeningUseCase(
                screenings, movies, cinemas, id_factory=lambda: str(uuid4())
            ),
            update=UpdateScreeningUseCase(screenings, movies, cinemas),
            delete=DeleteScreeningUseCase(screenings),
            screenings=screenings,
            movies=movies,
        )

    return WriteScreeningUseCase(
        SupabaseScreeningWriteTransaction(pool, build_session),
        clock=lambda: datetime.now(UTC),
    )
