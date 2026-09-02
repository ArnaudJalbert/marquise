"""Gateway-backed password authentication repository."""

from __future__ import annotations

from marquise.application.exceptions.auth import AuthenticationError
from marquise.application.repositories.password_authentication_repository import (
    PasswordAuthenticationRepository,
)
from marquise.interface_adapters.repositories.protocols.auth import (
    AuthGatewayError,
    PasswordAuthGateway,
)


class GatewayPasswordAuthenticationRepository(PasswordAuthenticationRepository):
    """Translate password-gateway failures into application errors."""

    def __init__(self, gateway: PasswordAuthGateway) -> None:
        """Initialize with password-authentication gateway."""
        self._gateway = gateway

    async def issue_access_token(self, email: str, password: str) -> str:
        """Authenticate credentials and return access token."""
        try:
            return await self._gateway.issue_access_token(email, password)
        except AuthGatewayError as exc:
            raise AuthenticationError("Email or password is invalid") from exc
