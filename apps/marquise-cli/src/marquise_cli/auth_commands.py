"""Administrator-authenticated Supabase account commands."""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass

from marquise import (
    ApplicationError,
    AuthenticationError,
    AuthFactory,
    AuthorizationError,
)
from marquise_cli.helpers import prompt_password, run_spinner


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """Supabase settings required by local account administration."""

    supabase_url: str
    publishable_key: str
    service_role_key: str


def load_auth_settings() -> AuthSettings:
    """Load required Supabase settings from environment."""
    names = (
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
    )
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )
    return AuthSettings(
        supabase_url=os.environ["SUPABASE_URL"].rstrip("/"),
        publishable_key=os.environ["SUPABASE_PUBLISHABLE_KEY"],
        service_role_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _administrator_credentials() -> tuple[str, str]:
    """Use configured credentials only when both values exist."""
    email = os.environ.get("MARQUISE_EMAIL")
    password = os.environ.get("MARQUISE_PASSWORD")
    if email and password:
        return email, password
    return input("Administrator email: "), prompt_password("Administrator password: ")


async def run_login(
    factory: AuthFactory,
    *,
    administrator_email: str,
    administrator_password: str,
) -> None:
    """Verify credentials have Administrator access without retaining a session."""
    authenticate = factory.authenticate_administrator_use_case
    await run_spinner(
        authenticate.execute(
            authenticate.InputData(
                email=administrator_email,
                password=administrator_password,
            )
        ),
        description="Authenticating Administrator...",
    )
    print("Authenticated as Administrator.")


async def run_invite(
    factory: AuthFactory,
    *,
    administrator_email: str,
    administrator_password: str,
    email: str,
    role: str,
) -> None:
    """Authenticate Administrator, then invite one human account."""
    authenticate = factory.authenticate_administrator_use_case
    await run_spinner(
        authenticate.execute(
            authenticate.InputData(
                email=administrator_email,
                password=administrator_password,
            )
        ),
        description="Authenticating Administrator...",
    )
    invite_account = factory.invite_account_use_case
    result = await run_spinner(
        invite_account.execute(invite_account.InputData(email=email, role=role)),
        description="Inviting user...",
    )
    print(f'Invited "{result.email}" as {result.role}.')


async def run_set_role(
    factory: AuthFactory,
    *,
    administrator_email: str,
    administrator_password: str,
    email: str,
    role: str | None,
) -> None:
    """Authenticate Administrator, then set or clear one human role."""
    authenticate = factory.authenticate_administrator_use_case
    administrator = await run_spinner(
        authenticate.execute(
            authenticate.InputData(
                email=administrator_email,
                password=administrator_password,
            )
        ),
        description="Authenticating Administrator...",
    )
    set_role_use_case = factory.set_account_role_use_case
    result = await run_spinner(
        set_role_use_case.execute(
            set_role_use_case.InputData(
                actor_account_id=administrator.subject,
                email=email,
                role=role,
            )
        ),
        description="Updating user role...",
    )
    print(f'Updated "{result.email}" role to {result.role or "none"}.')


def _factory(settings: AuthSettings) -> AuthFactory:
    return AuthFactory(
        settings.supabase_url,
        publishable_key=settings.publishable_key,
        service_role_key=settings.service_role_key,
    )


def login() -> None:
    """Verify local credentials have Administrator access."""
    try:
        settings = load_auth_settings()
        administrator_email, administrator_password = _administrator_credentials()
        asyncio.run(
            run_login(
                _factory(settings),
                administrator_email=administrator_email,
                administrator_password=administrator_password,
            )
        )
    except (AuthenticationError, AuthorizationError, ValueError) as exc:
        print(f"Failed to authenticate Administrator: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except (ApplicationError, RuntimeError) as exc:
        print(f"Failed to log in: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def invite(email: str, role: str) -> None:
    """Invite a human account with a fixed Marquise role."""
    try:
        settings = load_auth_settings()
        administrator_email, administrator_password = _administrator_credentials()
        asyncio.run(
            run_invite(
                _factory(settings),
                administrator_email=administrator_email,
                administrator_password=administrator_password,
                email=email,
                role=role,
            )
        )
    except (AuthenticationError, AuthorizationError) as exc:
        print(f"Failed to authenticate Administrator: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except (ApplicationError, RuntimeError, ValueError) as exc:
        print(f"Failed to invite user: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def set_role(email: str, role: str | None, clear_role: bool) -> None:
    """Set or clear a human account's Marquise role."""
    if (role is None and not clear_role) or (role is not None and clear_role):
        raise SystemExit("Exactly one of --role or --clear-role is required")
    try:
        settings = load_auth_settings()
        administrator_email, administrator_password = _administrator_credentials()
        asyncio.run(
            run_set_role(
                _factory(settings),
                administrator_email=administrator_email,
                administrator_password=administrator_password,
                email=email,
                role=None if clear_role else role,
            )
        )
    except (AuthenticationError, AuthorizationError) as exc:
        print(f"Failed to authenticate Administrator: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except (ApplicationError, RuntimeError, ValueError) as exc:
        print(f"Failed to update user role: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
