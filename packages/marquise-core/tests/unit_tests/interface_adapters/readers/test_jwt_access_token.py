"""Tests for deterministic JWT access-token verification."""

from __future__ import annotations

from unittest.mock import create_autospec

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from marquise.interface_adapters.exceptions.auth import (
    AuthGatewayError,
    AuthGatewayUnavailableError,
)
from marquise.interface_adapters.readers import (
    JwtAccessTokenGateway,
    SigningKeyProvider,
)

ISSUER = "https://project.supabase.co/auth/v1"
AUDIENCE = "authenticated"
VALID_EXPIRY = 4102444800


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    """Provide a local key pair for signed-token scenarios."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def jwt_gateway(private_key: rsa.RSAPrivateKey) -> JwtAccessTokenGateway:
    """Provide a verifier with an injected local signing key."""
    provider = create_autospec(SigningKeyProvider, instance=True)
    provider.get_signing_key.return_value = jwt.PyJWK.from_dict(
        jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), True)
    )
    return JwtAccessTokenGateway(provider, ISSUER, AUDIENCE)


def _token(
    private_key: rsa.RSAPrivateKey,
    **claims: str | int,
) -> str:
    payload: dict = {
        "sub": "user-id",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": VALID_EXPIRY,
        "app_metadata": {"marquise_role": "editor"},
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256")


@pytest.mark.asyncio
async def test_jwt_gateway_verifies_signature_and_registered_claims(
    jwt_gateway: JwtAccessTokenGateway,
    private_key: rsa.RSAPrivateKey,
) -> None:
    """A valid signed token returns trusted plain claims."""
    claims = await jwt_gateway.verify(_token(private_key))

    assert claims["sub"] == "user-id"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 0},
        {"iss": "https://other.supabase.co/auth/v1"},
        {"aud": "other"},
    ],
)
async def test_jwt_gateway_rejects_invalid_registered_claims(
    jwt_gateway: JwtAccessTokenGateway,
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, str | int],
) -> None:
    """Expired, wrong-issuer, and wrong-audience tokens fail verification."""
    with pytest.raises(AuthGatewayError):
        await jwt_gateway.verify(_token(private_key, **claims))


@pytest.mark.asyncio
async def test_jwt_gateway_rejects_bad_signature(
    jwt_gateway: JwtAccessTokenGateway,
) -> None:
    """A token signed by an untrusted key fails verification."""
    wrong_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    with pytest.raises(AuthGatewayError):
        await jwt_gateway.verify(_token(wrong_key))


@pytest.mark.asyncio
async def test_jwt_gateway_preserves_signing_key_outage() -> None:
    """The verifier does not turn a key-provider outage into an invalid token."""
    provider = create_autospec(SigningKeyProvider, instance=True)
    provider.get_signing_key.side_effect = AuthGatewayUnavailableError(
        "JWKS unavailable"
    )
    gateway = JwtAccessTokenGateway(provider, ISSUER, AUDIENCE)

    with pytest.raises(AuthGatewayUnavailableError, match="JWKS unavailable"):
        await gateway.verify("encoded-token")
