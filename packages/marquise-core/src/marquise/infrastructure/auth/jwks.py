"""Generic JSON Web Key Set access-token verifier."""

from __future__ import annotations

import jwt
from jwt.exceptions import PyJWKClientConnectionError

from marquise.interface_adapters.exceptions.auth import (
    AuthGatewayError,
    AuthGatewayUnavailableError,
)


class JwksSigningKeyProvider:
    """Verify access tokens using keys resolved from a JWKS endpoint."""

    def __init__(self, client: jwt.PyJWKClient) -> None:
        """Initialize with a JWKS client."""
        self._client = client

    def verify(self, token: str, issuer: str, audience: str) -> dict:
        """Verify a token and return plain claims to the adapter boundary."""
        try:
            key = self._client.get_signing_key_from_jwt(token)
            algorithm = key.algorithm_name
            if algorithm not in {"RS256", "ES256"}:
                raise AuthGatewayError("Unsupported JWT signing algorithm")
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                issuer=issuer,
                audience=audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
            if not isinstance(claims, dict):
                raise AuthGatewayError("Invalid JWT claims")
            return claims
        except PyJWKClientConnectionError as exc:
            raise AuthGatewayUnavailableError("Signing keys are unavailable") from exc
        except (jwt.PyJWTError, ValueError) as exc:
            raise AuthGatewayError("Access token verification failed") from exc
