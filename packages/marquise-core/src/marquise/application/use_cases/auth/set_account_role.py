"""Authenticate an Administrator and set a human account role."""

from __future__ import annotations

from dataclasses import dataclass, field

from marquise.application.exceptions.auth import (
    AccountNotFoundError,
    SelfDemotionError,
)
from marquise.application.repositories.account_repository import AccountRepository
from marquise.application.use_cases.auth._validation import normalize_email
from marquise.application.use_cases.auth.authenticate_administrator import (
    AuthenticateAdministratorUseCase,
)
from marquise.domain.value_objects.marquise_role import MarquiseRole


class SetAccountRoleUseCase:
    """Authorize and change protected role metadata without self-demotion."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Administrator credentials, target email, and replacement role."""

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
        """Updated account role details."""

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
        """Authorize the actor, resolve the target, and update role metadata.

        Administrator authentication is the authorization gate. If it fails,
        no target-account lookup or privileged provider operation is attempted.

        Raises:
            AuthenticationError: If the Administrator credentials are invalid.
            AuthenticationServiceUnavailableError: If authentication is unavailable.
            AuthorizationError: If the actor is not an Administrator.
            AccountNotFoundError: If the target account does not exist.
            SelfDemotionError: If the actor attempts to remove their own role.
            AuthAdministrationError: If the role update fails.
        """
        administrator_email = normalize_email(request.administrator_email)
        email = normalize_email(request.email)

        # This call fails before any privileged account operation when the actor
        # cannot be authenticated and authorized as an Administrator.
        actor = await self._authenticate_administrator.execute(
            self._authenticate_administrator.InputData(
                email=administrator_email,
                password=request.administrator_password,
            )
        )
        account = await self._accounts.find_by_email(email)
        if account is None:
            raise AccountNotFoundError(f'No account found with email "{email}"')

        role = MarquiseRole(request.role)
        if account.id == actor.subject and role is not MarquiseRole.ADMINISTRATOR:
            raise SelfDemotionError(
                "Administrators cannot remove their own Administrator role"
            )

        await self._accounts.set_role(account.id, role)
        return self.OutputData(
            account_id=account.id,
            email=account.email,
            role=role.value,
        )
