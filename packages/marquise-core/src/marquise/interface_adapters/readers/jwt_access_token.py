"""JWT access-token verification adapter."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

import jwt

from marquise.interface_adapters.repositories.protocols.auth import (
    AccessTokenGateway,
    AuthGatewayError,
)


class SigningKeyProvider(ABC):
    """Resolve a trusted signing key for an encoded JWT."""

    @abstractmethod
    def get_signing_key(self, token: str) -> jwt.PyJWK:
        """Return the key matching the token header."""
        ...


class JwtAccessTokenGateway(AccessTokenGateway):
    """Verify JWT signatures and registered claims using injected keys."""

    def __init__(
        self,
        signing_keys: SigningKeyProvider,
        issuer: str,
        audience: str = "authenticated",
    ) -> None:
        """Initialize trusted key provider and expected claims."""
        self._signing_keys = signing_keys
        self._issuer = issuer
        self._audience = audience

    async def verify(self, token: str) -> dict:
        """Verify a token without blocking async delivery workers."""
        return await asyncio.to_thread(self._verify, token)

    def _verify(self, token: str) -> dict:
        try:
            key = self._signing_keys.get_signing_key(token)
            algorithm = key.algorithm_name
            if algorithm not in {"RS256", "ES256"}:
                raise AuthGatewayError("Unsupported JWT signing algorithm")
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
            if not isinstance(claims, dict):
                raise AuthGatewayError("Invalid JWT claims")
            return claims
        except (jwt.PyJWTError, ValueError) as exc:
            raise AuthGatewayError("Access token verification failed") from exc
