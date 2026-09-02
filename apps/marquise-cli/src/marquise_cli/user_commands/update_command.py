"""User update CLI command."""

from __future__ import annotations

import asyncio
import getpass
import sys

from marquise_cli.auth import AuthClient, AuthSettings, RoleStore, load_auth_settings
from marquise_cli.helpers import run_spinner


async def _resolve_user_id(
    store: RoleStore,
    *,
    user_id: str | None,
    email: str | None,
) -> str:
    if user_id is not None:
        return user_id
    if email is None:
        raise ValueError("Either --id or --email is required")
    user = await store.get_user_by_email(email)
    if user is None:
        raise ValueError(f'No user found with email "{email}"')
    return user.id


async def run_update(
    settings: AuthSettings,
    *,
    user_id: str | None,
    email: str | None,
    new_email: str | None,
    password: str | None,
    role: str | None,
    clear_role: bool,
) -> None:
    auth = AuthClient(settings.supabase_url, settings.service_role_key)

    async with RoleStore(settings.database_url, settings.schema) as store:
        resolved_id = await _resolve_user_id(store, user_id=user_id, email=email)

        if new_email is not None or password is not None:
            await run_spinner(
                asyncio.to_thread(
                    auth.update_user,
                    resolved_id,
                    email=new_email,
                    password=password,
                ),
                description="Updating user...",
            )

        if clear_role:
            await run_spinner(
                store.clear_role(resolved_id),
                description="Clearing role...",
            )
        elif role is not None:
            await run_spinner(
                store.assign_role(resolved_id, role),
                description="Updating role...",
            )

        users = await store.search_users(email=new_email or email)
        updated = next((user for user in users if user.id == resolved_id), None)
        if updated is None and email is not None:
            updated = await store.get_user_by_email(email)

    if updated is None:
        updated_user = await asyncio.to_thread(auth.get_user, resolved_id)
        print("User updated:")
        print(f"  ID:    {updated_user.id}")
        print(f"  Email: {updated_user.email}")
        if role is not None:
            print(f"  Role:  {role.strip().lower()}")
        elif clear_role:
            print("  Role:  (none)")
        return

    print("User updated:")
    print(f"  ID:    {updated.id}")
    print(f"  Email: {updated.email}")
    print(f"  Role:  {updated.role_name or '(none)'}")


def update(
    user_id: str | None = None,
    email: str | None = None,
    new_email: str | None = None,
    password: str | None = None,
    role: str | None = None,
    clear_role: bool = False,
) -> None:
    """Update a user's email, password, and/or role."""
    try:
        settings = load_auth_settings()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    if user_id is None and email is None:
        email = input("User email: ") or None

    if new_email is None and password is None and role is None and not clear_role:
        new_email_input = input("New email (leave blank to keep): ")
        new_email = new_email_input.strip() or None
        password_input = getpass.getpass("New password (leave blank to keep): ")
        password = password_input or None
        role_input = input("Role (leave blank to keep, 'none' to clear): ")
        if role_input.strip().lower() == "none":
            clear_role = True
        elif role_input.strip():
            role = role_input.strip()

    try:
        asyncio.run(
            run_update(
                settings,
                user_id=user_id,
                email=email,
                new_email=new_email,
                password=password,
                role=role,
                clear_role=clear_role,
            )
        )
    except ValueError as error:
        print(f"Failed to update user: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except Exception as error:
        print(f"Failed to update user: {error}", file=sys.stderr)
        raise SystemExit(1) from error
