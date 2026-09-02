"""Set or clear a human account's Marquise role."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions.auth import (
    AuthUserNotFoundError,
    SelfDemotionError,
)
from marquise.application.repositories.user_identity_repository import (
    UserIdentityRepository,
)
from marquise.application.use_cases._auth_validation import normalize_email
from marquise.domain.value_objects.marquise_role import MarquiseRole


class SetAuthUserRoleUseCase:
    """Change protected role metadata while preventing self-demotion."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Actor, target email, and replacement role."""

        actor_user_id: str
        email: str
        role: str | None

        def __post_init__(self) -> None:
            """Validate actor, email, and optional role."""
            if not self.actor_user_id:
                raise ValueError("actor_user_id must not be empty")
            object.__setattr__(self, "email", normalize_email(self.email))
            if self.role is not None:
                MarquiseRole(self.role)

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Updated user role details."""

        user_id: str
        email: str
        role: str | None

    def __init__(self, users: UserIdentityRepository) -> None:
        """Initialize with Auth user repository."""
        self._users = users

    async def execute(self, request: InputData) -> OutputData:
        """Resolve target, prevent self-demotion, and update role metadata."""
        user = await self._users.find_by_email(request.email)
        if user is None:
            raise AuthUserNotFoundError(f'No user found with email "{request.email}"')

        role = MarquiseRole(request.role) if request.role is not None else None
        if user.id == request.actor_user_id and role is not MarquiseRole.ADMINISTRATOR:
            raise SelfDemotionError("Administrators cannot remove their own role")

        await self._users.set_role(user.id, role)
        return self.OutputData(
            user_id=user.id,
            email=user.email,
            role=role.value if role is not None else None,
        )
