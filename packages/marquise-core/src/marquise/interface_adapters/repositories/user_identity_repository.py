"""Gateway-backed user identity repository."""

from __future__ import annotations

from marquise.application.exceptions.auth import AuthAdministrationError
from marquise.application.repositories.user_identity_repository import (
    UserIdentityRepository,
)
from marquise.domain.entities.user_identity import UserIdentity
from marquise.domain.value_objects.marquise_role import MarquiseRole
from marquise.interface_adapters.repositories.protocols.auth import (
    AuthAdminGateway,
    AuthGatewayError,
)


class GatewayUserIdentityRepository(UserIdentityRepository):
    """Map Supabase Admin gateway data to user identities."""

    def __init__(self, gateway: AuthAdminGateway) -> None:
        """Initialize with Auth Admin gateway."""
        self._gateway = gateway

    async def invite(self, email: str) -> UserIdentity:
        """Invite a user and map returned data."""
        try:
            return self._to_identity(await self._gateway.invite(email))
        except (AuthGatewayError, ValueError) as exc:
            raise AuthAdministrationError("Unable to invite user") from exc

    async def find_by_email(self, email: str) -> UserIdentity | None:
        """Find a user by exact email."""
        try:
            data = await self._gateway.find_by_email(email)
            return self._to_identity(data) if data is not None else None
        except (AuthGatewayError, ValueError) as exc:
            raise AuthAdministrationError("Unable to find user") from exc

    async def set_role(self, user_id: str, role: MarquiseRole | None) -> None:
        """Set or clear protected Marquise role metadata."""
        try:
            await self._gateway.set_role(
                user_id, role.value if role is not None else None
            )
        except AuthGatewayError as exc:
            raise AuthAdministrationError("Unable to update user role") from exc

    async def delete(self, user_id: str) -> None:
        """Delete one user."""
        try:
            await self._gateway.delete(user_id)
        except AuthGatewayError as exc:
            raise AuthAdministrationError("Unable to delete user") from exc

    @staticmethod
    def _to_identity(data: dict) -> UserIdentity:
        """Map plain gateway user data to domain entity."""
        user_id = data.get("id")
        email = data.get("email")
        if not isinstance(user_id, str) or not isinstance(email, str):
            raise ValueError("invalid user identity")
        return UserIdentity(id=user_id, email=email)
