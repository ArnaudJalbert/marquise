"""Administrator-authenticated Supabase account commands."""

from __future__ import annotations

import asyncio
import os
import sys

from marquise import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    MarquiseFactory,
)
from marquise_cli.helpers import prompt_password, run_spinner


def _administrator_credentials() -> tuple[str, str]:
    """Use configured credentials only when both values exist."""
    email = os.environ.get("MARQUISE_EMAIL")
    password = os.environ.get("MARQUISE_PASSWORD")
    if email and password:
        return email, password
    return input("Administrator email: "), prompt_password("Administrator password: ")


async def run_invite(
    factory: MarquiseFactory,
    *,
    administrator_email: str,
    administrator_password: str,
    email: str,
    role: str,
) -> None:
    """Run the authorized human-account invitation workflow."""
    invite_account = factory.invite_account_use_case
    result = await run_spinner(
        invite_account.execute(
            invite_account.InputData(
                administrator_email=administrator_email,
                administrator_password=administrator_password,
                email=email,
                role=role,
            )
        ),
        description="Inviting account...",
    )
    print(f'Invited account "{result.email}" as {result.role}.')


async def run_set_role(
    factory: MarquiseFactory,
    *,
    administrator_email: str,
    administrator_password: str,
    email: str,
    role: str,
) -> None:
    """Run the authorized human-account role-change workflow."""
    set_role_use_case = factory.set_account_role_use_case
    result = await run_spinner(
        set_role_use_case.execute(
            set_role_use_case.InputData(
                administrator_email=administrator_email,
                administrator_password=administrator_password,
                email=email,
                role=role,
            )
        ),
        description="Updating account role...",
    )
    print(f'Updated account "{result.email}" role to {result.role}.')


def invite(email: str, role: str) -> None:
    """Invite a human account with a fixed Marquise role."""
    try:
        administrator_email, administrator_password = _administrator_credentials()
        asyncio.run(
            run_invite(
                MarquiseFactory(),
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
        print(f"Failed to invite account: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def set_role(email: str, role: str) -> None:
    """Set a human account's Marquise role."""
    try:
        administrator_email, administrator_password = _administrator_credentials()
        asyncio.run(
            run_set_role(
                MarquiseFactory(),
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
        print(f"Failed to update account role: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
