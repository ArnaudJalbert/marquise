"""Generic JSON Web Key Set signing-key provider."""

from __future__ import annotations

import jwt
from jwt.exceptions import PyJWKClientConnectionError

from marquise.interface_adapters.exceptions.auth import (
    AuthGatewayUnavailableError,
)


class JwksSigningKeyProvider:
    """Resolve signing keys through an injected JWKS client."""

    def __init__(self, client: jwt.PyJWKClient) -> None:
        """Initialize with a JWKS client."""
        self._client = client

    def get_signing_key(self, token: str) -> jwt.PyJWK:
        """Return the trusted signing key selected by token key ID."""
        try:
            return self._client.get_signing_key_from_jwt(token)
        except PyJWKClientConnectionError as exc:
            raise AuthGatewayUnavailableError("Signing keys are unavailable") from exc
