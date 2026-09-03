"""Gateway-backed authenticated identity reader."""

from __future__ import annotations

from marquise.application.exceptions.auth import (
    AuthenticationError,
    AuthenticationServiceUnavailableError,
)
from marquise.application.readers.account_identity_reader import AccountIdentityReader
from marquise.domain.value_objects.marquise_role import MarquiseRole
from marquise.interface_adapters.exceptions.auth import (
    AuthGatewayError,
    AuthGatewayUnavailableError,
)
from marquise.interface_adapters.repositories.protocols.auth import AccessTokenGateway


class GatewayAccountIdentityReader(AccountIdentityReader):
    """Map verified plain JWT claims to minimal read data."""

    def __init__(self, gateway: AccessTokenGateway) -> None:
        """Initialize with access-token gateway."""
        self._gateway = gateway

    async def read(self, token: str) -> AccountIdentityReader.IdentityData:
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
        except AuthGatewayUnavailableError as exc:
            raise AuthenticationServiceUnavailableError(
                "Authentication service is unavailable"
            ) from exc
        except (AuthGatewayError, ValueError) as exc:
            raise AuthenticationError("Access token is invalid") from exc
