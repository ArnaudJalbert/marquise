"""Invite a human account with a Marquise role."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions.auth import AuthAdministrationError
from marquise.application.repositories.account_repository import AccountRepository
from marquise.application.use_cases._auth_validation import normalize_email
from marquise.domain.value_objects.marquise_role import MarquiseRole


class InviteAccountUseCase:
    """Invite an account, assign protected role metadata, and roll back failures."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Invitation target and fixed Marquise role."""

        email: str
        role: str

        def __post_init__(self) -> None:
            """Normalize email and validate role."""
            object.__setattr__(self, "email", normalize_email(self.email))
            MarquiseRole(self.role)

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Invited account details."""

        account_id: str
        email: str
        role: str

    def __init__(self, accounts: AccountRepository) -> None:
        """Initialize with Auth account repository."""
        self._accounts = accounts

    async def execute(self, request: InputData) -> OutputData:
        """Invite account and attach role metadata atomically where possible."""
        role = MarquiseRole(request.role)
        account = await self._accounts.invite(request.email)
        try:
            await self._accounts.set_role(account.id, role)
        except AuthAdministrationError:
            try:
                await self._accounts.delete(account.id)
            except AuthAdministrationError as rollback_exc:
                raise AuthAdministrationError(
                    "Invitation role assignment and rollback failed"
                ) from rollback_exc
            raise
        return self.OutputData(
            account_id=account.id, email=account.email, role=role.value
        )
