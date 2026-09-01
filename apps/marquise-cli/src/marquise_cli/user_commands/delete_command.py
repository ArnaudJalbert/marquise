"""User deletion CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise_cli.auth import AuthClient, AuthSettings, RoleStore, load_auth_settings
from marquise_cli.helpers import run_spinner


async def _resolve_user(
    store: RoleStore,
    *,
    user_id: str | None,
    email: str | None,
) -> tuple[str, str | None]:
    if user_id is not None:
        if email is not None:
            return user_id, email
        users = await store.search_users(email=None, query=None)
        match = next((user for user in users if user.id == user_id), None)
        return user_id, match.email if match else None

    if email is not None:
        user = await store.get_user_by_email(email)
        if user is None:
            raise ValueError(f'No user found with email "{email}"')
        return user.id, user.email

    users = await store.search_users()
    if not users:
        print("No users available to delete.")
        raise SystemExit(0)

    choices = [
        questionary.Choice(
            title=f"{user.email or user.id} [{user.role_name or 'no role'}]",
            value=user,
        )
        for user in users
    ]
    choices.append(questionary.Choice(title="← exit", value="__exit__"))
    selected = await questionary.select(
        "Select a user to delete:",
        choices=choices,
    ).ask_async()
    if selected is None or selected == "__exit__":
        print("Cancelled.")
        raise SystemExit(0)
    return selected.id, selected.email


async def _confirm_deletion(email: str | None, user_id: str) -> bool:
    label = email or user_id
    confirmed = await questionary.confirm(
        f'Delete user "{label}"?',
        default=False,
    ).ask_async()
    if confirmed is None:
        print("Cancelled.")
        return False
    return confirmed


async def run_delete(
    settings: AuthSettings,
    *,
    user_id: str | None,
    email: str | None,
) -> None:
    auth = AuthClient(settings.supabase_url, settings.service_role_key)
    async with RoleStore(settings.database_url, settings.schema) as store:
        resolved_id, resolved_email = await _resolve_user(
            store,
            user_id=user_id,
            email=email,
        )
        if user_id is None and email is None:
            if not await _confirm_deletion(resolved_email, resolved_id):
                return

        await run_spinner(
            asyncio.to_thread(auth.delete_user, resolved_id),
            description="Deleting user...",
        )

    label = resolved_email or resolved_id
    print(f'User "{label}" deleted.')


def delete(user_id: str | None = None, email: str | None = None) -> None:
    """Delete a user by ID or email."""
    try:
        settings = load_auth_settings()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    if user_id is None and email is None:
        email = input("User email (leave blank to pick from list): ") or None

    try:
        asyncio.run(run_delete(settings, user_id=user_id, email=email))
    except ValueError as error:
        print(f"Failed to delete user: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except Exception as error:
        print(f"Failed to delete user: {error}", file=sys.stderr)
        raise SystemExit(1) from error
