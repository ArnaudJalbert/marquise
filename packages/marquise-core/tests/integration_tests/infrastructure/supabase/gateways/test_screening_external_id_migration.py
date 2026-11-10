"""Verify schema bootstrap and external-ID migration on isolated test schemas."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import SupabaseScreeningGateway
from marquise.infrastructure.supabase.gateways.screening_reader import (
    SupabaseScreeningReadGateway,
)
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningExternalIdConflictGatewayError,
)

SCRIPTS = Path(__file__).resolve().parents[7] / "scripts"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bootstrap", ["marquise-schema.sql", "marquise-test-schema.sql"]
)
async def test_external_id_migration_preserves_rows_and_refuses_unsafe_rollback(
    db_pool: asyncpg.Pool, bootstrap: str
) -> None:
    """Bootstrap and upgrade allow shared IDs; unsafe rollback preserves both rows."""
    schema = f"migration_{uuid4().hex}"
    cinema = SupabaseCinemaGateway(db_pool, schema)
    movie = SupabaseMovieGateway(db_pool, schema)
    screening = SupabaseScreeningGateway(db_pool, schema)
    showtime = datetime(2026, 10, 7, 17, tzinfo=UTC)
    async with db_pool.acquire() as conn:
        try:
            sql = (SCRIPTS / bootstrap).read_text().replace("marquise-test", schema)
            await conn.execute(sql.replace("marquise", schema))
            for cinema_id in ("royalmount", "cinematheque"):
                await cinema.save(cinema_id, cinema_id, address=None, city=None)
            await movie.save("tony", "Tony", release_year=None)
            await movie.save("nitassinan", "Nitassinan", release_year=None)
            await screening.save("owner", "tony", "royalmount", showtime, "14384")
            await screening.save(
                "target", "nitassinan", "cinematheque", showtime, "14384"
            )
            reader = SupabaseScreeningReadGateway(db_pool, schema)
            assert (await reader.search()).total == 2
            await screening.delete("target")
            # Historical global constraint, as installed before #285.
            await conn.execute(
                f'ALTER TABLE "{schema}".screenings '
                "DROP CONSTRAINT screenings_external_id_key, "
                "ADD CONSTRAINT screenings_external_id_key UNIQUE (external_id)"
            )
            before = await screening.find_by_id("owner")
            forward = (
                SCRIPTS / "migrations/285-cinema-scoped-external-id.sql"
            ).read_text()
            rollback = (
                SCRIPTS / "migrations/285-cinema-scoped-external-id-rollback.sql"
            ).read_text()
            await conn.execute(
                forward.replace("marquise.screenings", f'"{schema}".screenings')
            )
            assert await screening.find_by_id("owner") == before
            # delete() removes the now-orphaned target movie, so recreate it.
            await movie.save("nitassinan", "Nitassinan", release_year=None)
            await screening.save(
                "target", "nitassinan", "cinematheque", showtime, "14384"
            )
            target_before = await screening.find_by_id("target")

            with pytest.raises(asyncpg.UniqueViolationError):
                await conn.execute(
                    rollback.replace("marquise.screenings", f'"{schema}".screenings')
                )
            await conn.execute("ROLLBACK")
            assert await screening.find_by_id("owner") == before
            assert await screening.find_by_id("target") == target_before
            # The failed rollback also preserves cinema-scoped protection.
            with pytest.raises(ScreeningExternalIdConflictGatewayError):
                await screening.save(
                    "conflict", "tony", "cinematheque", showtime, "14384"
                )

            await screening.delete("target")
            await conn.execute(
                rollback.replace("marquise.screenings", f'"{schema}".screenings')
            )
            assert await screening.find_by_id("owner") == before
            await movie.save("nitassinan", "Nitassinan", release_year=None)
            with pytest.raises(ScreeningExternalIdConflictGatewayError):
                await screening.save(
                    "target", "nitassinan", "cinematheque", showtime, "14384"
                )
        finally:
            await conn.execute("ROLLBACK")
            await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
