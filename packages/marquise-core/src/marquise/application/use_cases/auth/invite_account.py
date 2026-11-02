"""Authenticate an Administrator and invite a human account."""

from __future__ import annotations

from dataclasses import dataclass, field

from marquise.application.exceptions.auth import AccountAlreadyExistsError
from marquise.application.repositories.account_repository import AccountRepository
from marquise.application.use_cases.auth._validation import normalize_email
from marquise.application.use_cases.auth.authenticate_administrator import (
    AuthenticateAdministratorUseCase,
)
from marquise.domain.value_objects.marquise_role import MarquiseRole


class InviteAccountUseCase:
    """Authorize, invite a new account, and assign protected role metadata."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Administrator credentials, invitation target, and Marquise role."""

        administrator_email: str
        administrator_password: str = field(repr=False)
        email: str
        role: str

        def __post_init__(self) -> None:
            """Validate credentials, target email, and role."""
            normalize_email(self.administrator_email)
            if not self.administrator_password:
                raise ValueError("administrator_password must not be empty")
            normalize_email(self.email)
            if not MarquiseRole.is_valid(self.role):
                raise ValueError(f'Unsupported Marquise role: "{self.role}"')

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

    async def execute(self, input_data: InputData) -> OutputData:
        """Authorize the actor, invite a new account, and attach its role.

        Administrator authentication is the authorization gate. If it fails,
        no target-account lookup or privileged provider operation is attempted.

        Raises:
            AuthenticationError: If the Administrator credentials are invalid.
            AuthenticationServiceUnavailableError: If authentication is unavailable.
            AuthorizationError: If the actor is not an Administrator.
            AccountAlreadyExistsError: If the target email already exists.
            AuthAdministrationError: If invitation or role assignment fails.
        """
        administrator_email = normalize_email(input_data.administrator_email)
        email = normalize_email(input_data.email)

        # This call fails before any privileged account operation when the actor
        # cannot be authenticated and authorized as an Administrator.
        await self._authenticate_administrator.execute(
            self._authenticate_administrator.InputData(
                email=administrator_email,
                password=input_data.administrator_password,
            )
        )
        if await self._accounts.find_by_email(email) is not None:
            raise AccountAlreadyExistsError(
                f'An account already exists with email "{email}"'
            )

        role = MarquiseRole(input_data.role)
        account = await self._accounts.invite(email)
        await self._accounts.set_role(account.id, role)
        return self.OutputData(
            account_id=account.id,
            email=account.email,
            role=role.value,
        )
