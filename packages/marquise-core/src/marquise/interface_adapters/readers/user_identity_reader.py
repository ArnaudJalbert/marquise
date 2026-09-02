"""Gateway-backed authenticated identity reader."""

from __future__ import annotations

from marquise.application.exceptions.auth import AuthenticationError
from marquise.application.readers.user_identity_reader import UserIdentityReader
from marquise.domain.value_objects.marquise_role import MarquiseRole
from marquise.interface_adapters.repositories.protocols.auth import (
    AccessTokenGateway,
    AuthGatewayError,
)


class GatewayUserIdentityReader(UserIdentityReader):
    """Map verified plain JWT claims to minimal read data."""

    def __init__(self, gateway: AccessTokenGateway) -> None:
        """Initialize with access-token gateway."""
        self._gateway = gateway

    async def read(self, token: str) -> UserIdentityReader.IdentityData:
        """Verify token and map only subject and Marquise role."""
        try:
            claims = await self._gateway.verify(token)
            metadata = claims.get("app_metadata")
            role = metadata.get("marquise_role") if isinstance(metadata, dict) else None
            subject = claims.get("sub")
            if not isinstance(subject, str) or not subject:
                raise ValueError("invalid subject")
            return self.IdentityData(
                subject=subject,
                role=MarquiseRole(role).value,
            )
        except (AuthGatewayError, ValueError) as exc:
            raise AuthenticationError("Access token is invalid") from exc
