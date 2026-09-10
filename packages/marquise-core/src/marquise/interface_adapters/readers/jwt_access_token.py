"""JWT access-token verification adapter."""

from __future__ import annotations

import asyncio

from marquise.interface_adapters.repositories.protocols.auth import (
    AccessTokenGateway,
    SigningKeyProvider,
)


class JwtAccessTokenGateway(AccessTokenGateway):
    """Adapt a token verifier to the application access-token gateway."""

    def __init__(
        self,
        signing_keys: SigningKeyProvider,
        issuer: str,
        audience: str = "authenticated",
    ) -> None:
        """Initialize trusted verifier and expected claims."""
        self._signing_keys = signing_keys
        self._issuer = issuer
        self._audience = audience

    async def verify(self, token: str) -> dict:
        """Verify a token without blocking async delivery workers."""
        return await asyncio.to_thread(
            self._signing_keys.verify,
            token,
            self._issuer,
            self._audience,
        )
