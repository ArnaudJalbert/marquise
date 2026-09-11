"""Administrator-authenticated Supabase account commands."""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Callable, Coroutine

from marquise import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    MarquiseFactory,
)
from marquise_cli.helpers import prompt_password, run_spinner


class CredentialInputError(RuntimeError):
    """Raised when Administrator credentials cannot be read interactively."""


class CredentialPromptCancellationError(CredentialInputError):
    """Raised when the Administrator cancels credential entry."""


def _administrator_credentials() -> tuple[str, str]:
    """Use configured credentials only when both values exist."""
    email = os.environ.get("MARQUISE_EMAIL")
    password = os.environ.get("MARQUISE_PASSWORD")
    if email and password:
        return email, password
    try:
        email = input("Administrator email: ")
        password = prompt_password("Administrator password: ")
    except EOFError as exc:
        raise CredentialInputError(
            "Interactive input is unavailable. Set both MARQUISE_EMAIL and "
            "MARQUISE_PASSWORD for noninteractive use."
        ) from exc
    except KeyboardInterrupt as exc:
        raise CredentialPromptCancellationError(
            "Administrator credential entry cancelled."
        ) from exc
    if not email or not password:
        raise CredentialPromptCancellationError(
            "Administrator credential entry cancelled."
        )
    return email, password


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


def _run_account_command(
    workflow: Callable[..., Coroutine[object, object, None]],
    *,
    email: str,
    role: str,
    failure_action: str,
) -> None:
    """Run an Administrator-authenticated account command."""
    try:
        administrator_email, administrator_password = _administrator_credentials()
        asyncio.run(
            workflow(
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
    except CredentialPromptCancellationError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(130) from exc
    except CredentialInputError as exc:
        print(f"Failed to read Administrator credentials: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except (ApplicationError, RuntimeError, ValueError) as exc:
        print(f"Failed to {failure_action}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def invite(email: str, role: str) -> None:
    """Invite a human account with a fixed Marquise role."""
    _run_account_command(
        run_invite,
        email=email,
        role=role,
        failure_action="invite account",
    )


def set_role(email: str, role: str) -> None:
    """Set a human account's Marquise role."""
    _run_account_command(
        run_set_role,
        email=email,
        role=role,
        failure_action="update account role",
    )
