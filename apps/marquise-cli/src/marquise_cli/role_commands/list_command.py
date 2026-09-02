"""Role listing CLI command."""

from __future__ import annotations

import asyncio
import sys

from marquise_cli.auth import AuthSettings, RoleStore, load_auth_settings
from marquise_cli.auth.formatting import print_roles
from marquise_cli.helpers import run_spinner


async def run_list_roles(settings: AuthSettings) -> None:
    async with RoleStore(settings.database_url, settings.schema) as store:
        roles = await run_spinner(store.list_roles(), description="Fetching roles...")
    print_roles(roles)


def list_roles() -> None:
    """List all roles."""
    try:
        settings = load_auth_settings()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    asyncio.run(run_list_roles(settings))
