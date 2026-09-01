"""User creation CLI command."""

from __future__ import annotations

import asyncio
import getpass
import sys

from marquise_cli.auth import AuthClient, AuthSettings, RoleStore, load_auth_settings
from marquise_cli.helpers import run_spinner


async def run_create(
    settings: AuthSettings,
    *,
    email: str,
    password: str,
    role: str | None,
) -> None:
    auth = AuthClient(settings.supabase_url, settings.service_role_key)
    user = await run_spinner(
        asyncio.to_thread(
            auth.create_user,
            email=email,
            password=password,
        ),
        description="Creating user...",
    )

    assigned_role: str | None = None
    if role is not None:
        async with RoleStore(settings.database_url, settings.schema) as store:
            await run_spinner(
                store.assign_role(user.id, role),
                description="Assigning role...",
            )
            assigned_role = role.strip().lower()

    print("User created:")
    print(f"  ID:    {user.id}")
    print(f"  Email: {user.email}")
    if assigned_role:
        print(f"  Role:  {assigned_role}")


def create(
    email: str | None = None,
    password: str | None = None,
    role: str | None = None,
) -> None:
    """Create a user and optionally assign a role."""
    try:
        settings = load_auth_settings()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    email = email or input("Email: ")
    password = password or getpass.getpass("Password: ")
    if role is None:
        role_input = input("Role (optional): ")
        role = role_input.strip() or None

    try:
        asyncio.run(run_create(settings, email=email, password=password, role=role))
    except ValueError as error:
        print(f"Failed to create user: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except Exception as error:
        print(f"Failed to create user: {error}", file=sys.stderr)
        raise SystemExit(1) from error
