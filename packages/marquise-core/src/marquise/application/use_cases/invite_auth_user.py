"""Invite a human account with a Marquise role."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions.auth import AuthAdministrationError
from marquise.application.repositories.user_identity_repository import (
    UserIdentityRepository,
)
from marquise.application.use_cases._auth_validation import normalize_email
from marquise.domain.value_objects.marquise_role import MarquiseRole


class InviteAuthUserUseCase:
    """Invite a user, assign protected role metadata, and roll back failures."""

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
        """Invited user details."""

        user_id: str
        email: str
        role: str

    def __init__(self, users: UserIdentityRepository) -> None:
        """Initialize with Auth user repository."""
        self._users = users

    async def execute(self, request: InputData) -> OutputData:
        """Invite user and attach role metadata atomically where possible."""
        role = MarquiseRole(request.role)
        user = await self._users.invite(request.email)
        try:
            await self._users.set_role(user.id, role)
        except AuthAdministrationError:
            try:
                await self._users.delete(user.id)
            except AuthAdministrationError as rollback_exc:
                raise AuthAdministrationError(
                    "Invitation role assignment and rollback failed"
                ) from rollback_exc
            raise
        return self.OutputData(user_id=user.id, email=user.email, role=role.value)
