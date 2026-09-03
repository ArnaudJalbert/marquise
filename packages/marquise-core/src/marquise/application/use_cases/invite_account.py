"""Authenticate an Administrator and invite a human account."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.use_cases._auth_validation import normalize_email
from marquise.application.use_cases.authenticate_administrator import (
    AuthenticateAdministratorUseCase,
)

from marquise.application.exceptions.auth import AccountAlreadyExistsError
from marquise.application.repositories.account_repository import AccountRepository
from marquise.domain.value_objects.marquise_role import MarquiseRole


class InviteAccountUseCase:
    """Authorize, invite a new account, and assign protected role metadata."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Administrator credentials, invitation target, and Marquise role."""

        administrator_email: str
        administrator_password: str
        email: str
        role: str

        def __post_init__(self) -> None:
            """Normalize emails and validate credentials and role."""
            object.__setattr__(
                self,
                "administrator_email",
                normalize_email(self.administrator_email),
            )
            if not self.administrator_password:
                raise ValueError("administrator_password must not be empty")
            object.__setattr__(self, "email", normalize_email(self.email))
            MarquiseRole(self.role)

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Invited account details."""

        account_id: str
        email: str
        role: str

    def __init__(
        self,
        accounts: AccountRepository,
        authenticate_administrator: AuthenticateAdministratorUseCase,
    ) -> None:
        """Initialize with account storage and Administrator authentication."""
        self._accounts = accounts
        self._authenticate_administrator = authenticate_administrator

    async def execute(self, request: InputData) -> OutputData:
        """Authorize the actor, invite a new account, and attach its role."""
        await self._authenticate_administrator.execute(
            self._authenticate_administrator.InputData(
                email=request.administrator_email,
                password=request.administrator_password,
            )
        )
        if await self._accounts.find_by_email(request.email) is not None:
            raise AccountAlreadyExistsError(
                f'An account already exists with email "{request.email}"'
            )

        role = MarquiseRole(request.role)
        account = await self._accounts.invite(request.email)
        await self._accounts.set_role(account.id, role)
        return self.OutputData(
            account_id=account.id,
            email=account.email,
            role=role.value,
        )
