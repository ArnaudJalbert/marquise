"""Set or clear a human account's Marquise role."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions.auth import (
    AccountNotFoundError,
    SelfDemotionError,
)
from marquise.application.repositories.account_repository import AccountRepository
from marquise.application.use_cases._auth_validation import normalize_email
from marquise.domain.value_objects.marquise_role import MarquiseRole


class SetAccountRoleUseCase:
    """Change protected role metadata while preventing self-demotion."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Actor, target email, and replacement role."""

        actor_account_id: str
        email: str
        role: str | None

        def __post_init__(self) -> None:
            """Validate actor, email, and optional role."""
            if not self.actor_account_id:
                raise ValueError("actor_account_id must not be empty")
            object.__setattr__(self, "email", normalize_email(self.email))
            if self.role is not None:
                MarquiseRole(self.role)

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Updated account role details."""

        account_id: str
        email: str
        role: str | None

    def __init__(self, accounts: AccountRepository) -> None:
        """Initialize with Auth account repository."""
        self._accounts = accounts

    async def execute(self, request: InputData) -> OutputData:
        """Resolve target, prevent self-demotion, and update role metadata."""
        account = await self._accounts.find_by_email(request.email)
        if account is None:
            raise AccountNotFoundError(f'No account found with email "{request.email}"')

        role = MarquiseRole(request.role) if request.role is not None else None
        if (
            account.id == request.actor_account_id
            and role is not MarquiseRole.ADMINISTRATOR
        ):
            raise SelfDemotionError("Administrators cannot remove their own role")

        await self._accounts.set_role(account.id, role)
        return self.OutputData(
            account_id=account.id,
            email=account.email,
            role=role.value if role is not None else None,
        )
