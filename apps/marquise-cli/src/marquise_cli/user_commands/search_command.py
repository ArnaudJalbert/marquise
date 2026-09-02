"""User search CLI command."""

from __future__ import annotations

import asyncio
import sys

from marquise_cli.auth import AuthSettings, RoleStore, load_auth_settings
from marquise_cli.auth.formatting import print_users
from marquise_cli.helpers import run_spinner


async def run_search(
    settings: AuthSettings,
    *,
    email: str | None,
    query: str | None,
    verbose: bool,
) -> None:
    async with RoleStore(settings.database_url, settings.schema) as store:
        users = await run_spinner(
            store.search_users(email=email, query=query),
            description="Searching users...",
        )
    print_users(users, verbose=verbose)


def search(
    email: str | None = None,
    query: str | None = None,
    verbose: bool = False,
) -> None:
    """Search users by email or query substring."""
    try:
        settings = load_auth_settings()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    if email is None and query is None:
        query = input("Search query (email substring): ") or None

    asyncio.run(run_search(settings, email=email, query=query, verbose=verbose))
