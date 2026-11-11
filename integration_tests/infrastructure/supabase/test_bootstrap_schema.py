"""Verify the bootstrap scripts create a fresh schema without the write tables."""

from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

SCRIPTS = Path(__file__).resolve().parents[6] / "scripts"

WRITE_TABLES = ("screening_write_audit", "screening_write_results")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bootstrap", ["marquise-schema.sql", "marquise-test-schema.sql"]
)
async def test_bootstrap_omits_manual_write_tables(
    db_pool: asyncpg.Pool, bootstrap: str
) -> None:
    """A fresh bootstrap creates no screening write tables."""
    schema = f"bootstrap_{uuid4().hex}"
    async with db_pool.acquire() as conn:
        try:
            sql = (SCRIPTS / bootstrap).read_text().replace("marquise-test", schema)
            await conn.execute(sql.replace("marquise", schema))
            for table in WRITE_TABLES:
                assert (
                    await conn.fetchval("SELECT to_regclass($1)", f'"{schema}".{table}')
                    is None
                )
        finally:
            await conn.execute("ROLLBACK")
            await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
