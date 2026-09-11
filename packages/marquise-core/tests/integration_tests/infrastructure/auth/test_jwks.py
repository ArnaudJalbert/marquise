"""Tests for JWKS-backed token verification."""

from __future__ import annotations

from unittest.mock import create_autospec

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from marquise.infrastructure.auth.jwks import JwksSigningKeyProvider
from marquise.interface_adapters.exceptions.auth import (
    AuthGatewayError,
    AuthGatewayUnavailableError,
)

ISSUER = "https://project.supabase.co/auth/v1"
AUDIENCE = "authenticated"
VALID_EXPIRY = 4102444800


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    """Provide a local key pair for signed-token scenarios."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _token(private_key: rsa.RSAPrivateKey, **claims: str | int) -> str:
    payload: dict = {
        "sub": "user-id",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": VALID_EXPIRY,
        "app_metadata": {"marquise_role": "editor"},
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256")


@pytest.fixture
def provider(private_key: rsa.RSAPrivateKey) -> JwksSigningKeyProvider:
    """Provide a verifier backed by a deterministic fake JWKS client."""
    client = create_autospec(jwt.PyJWKClient, instance=True)
    client.get_signing_key_from_jwt.return_value = jwt.PyJWK.from_dict(
        jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), True)
    )
    return JwksSigningKeyProvider(client)


def test_provider_verifies_signature_and_registered_claims(
    provider: JwksSigningKeyProvider,
    private_key: rsa.RSAPrivateKey,
) -> None:
    """A valid signed token returns trusted plain claims."""
    claims = provider.verify(_token(private_key), ISSUER, AUDIENCE)
    assert claims["sub"] == "user-id"


@pytest.mark.parametrize(
    "claims",
    [{"exp": 0}, {"iss": "https://other.supabase.co/auth/v1"}, {"aud": "other"}],
)
def test_provider_rejects_invalid_registered_claims(
    provider: JwksSigningKeyProvider,
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, str | int],
) -> None:
    """Expired, wrong-issuer, and wrong-audience tokens fail verification."""
    with pytest.raises(AuthGatewayError):
        provider.verify(_token(private_key, **claims), ISSUER, AUDIENCE)


def test_provider_rejects_bad_signature(provider: JwksSigningKeyProvider) -> None:
    """A token signed by an untrusted key fails verification."""
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(AuthGatewayError):
        provider.verify(_token(wrong_key), ISSUER, AUDIENCE)


def test_provider_preserves_signing_key_outage() -> None:
    """A JWKS outage remains distinguishable from an invalid token."""
    client = create_autospec(jwt.PyJWKClient, instance=True)
    client.get_signing_key_from_jwt.side_effect = (
        jwt.exceptions.PyJWKClientConnectionError("JWKS unavailable")
    )
    with pytest.raises(
        AuthGatewayUnavailableError, match="Signing keys are unavailable"
    ):
        JwksSigningKeyProvider(client).verify("encoded-token", ISSUER, AUDIENCE)
