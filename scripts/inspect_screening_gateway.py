"""Ad-hoc script: call SupabaseScreeningGateway directly and print raw rows.

Bypasses the repository/domain mapping layers entirely, so you see exactly
what SQL returns from the ``screenings`` table (joined with ``movies`` and
``cinemas``) — useful for checking whether columns like ``ticket_url``,
``room``, and ``language`` are actually populated in the database.

Usage:
    uv run python scripts/inspect_screening_gateway.py --cinema-id <id> \\
        --from 2026-07-01 --to 2026-07-31

    uv run python scripts/inspect_screening_gateway.py --screening-id <id>
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from pprint import pprint

import asyncpg
from dotenv import load_dotenv

from marquise.infrastructure.supabase.database import sanitize_dsn
from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screening-id", help="Look up a single screening by ID.")
    parser.add_argument(
        "--cinema-id", help="Look up screenings for a cinema in a date range."
    )
    parser.add_argument(
        "--from",
        dest="start_date",
        help="Start of range (YYYY-MM-DD), required with --cinema-id.",
    )
    parser.add_argument(
        "--to",
        dest="end_date",
        help="End of range (YYYY-MM-DD), required with --cinema-id.",
    )
    return parser.parse_args()


async def run() -> None:
    """Connect to the database and print what the gateway returns."""
    load_dotenv()
    args = _parse_args()

    dsn = sanitize_dsn(os.environ["DATABASE_URL"])
    schema = os.environ.get("DATABASE_SCHEMA", "marquise")

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=1)
    try:
        gateway = SupabaseScreeningGateway(pool, schema=schema)

        if args.screening_id:
            row = await gateway.find_by_id(screening_id=args.screening_id)
            pprint(row)
        elif args.cinema_id:
            if not args.start_date or not args.end_date:
                raise SystemExit("--cinema-id requires both --from and --to")
            rows = await gateway.find_by_cinema_and_date_range(
                cinema_id=args.cinema_id,
                start_date=datetime.fromisoformat(args.start_date),
                end_date=datetime.fromisoformat(args.end_date),
            )
            print(f"{len(rows)} row(s)")
            for row in rows:
                pprint(row)
        else:
            raise SystemExit("Pass either --screening-id or --cinema-id")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run())
