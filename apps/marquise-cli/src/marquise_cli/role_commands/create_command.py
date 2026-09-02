"""Role creation CLI command."""

from __future__ import annotations

import asyncio
import sys

from marquise_cli.auth import AuthSettings, RoleStore, load_auth_settings
from marquise_cli.helpers import run_spinner


async def run_create(
    settings: AuthSettings,
    *,
    name: str,
    description: str | None,
) -> None:
    async with RoleStore(settings.database_url, settings.schema) as store:
        role = await run_spinner(
            store.create_role(name, description),
            description="Creating role...",
        )
    print("Role created:")
    print(f"  Name:        {role.name}")
    if role.description:
        print(f"  Description: {role.description}")


def create(name: str | None = None, description: str | None = None) -> None:
    """Create a role from arguments or interactive prompts."""
    try:
        settings = load_auth_settings()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    name = name or input("Role name: ")
    if description is None:
        description_input = input("Description (optional): ")
        description = description_input.strip() or None

    try:
        asyncio.run(run_create(settings, name=name, description=description))
    except ValueError as error:
        print(f"Failed to create role: {error}", file=sys.stderr)
        raise SystemExit(1) from error
