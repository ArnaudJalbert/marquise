"""Tests for the JWT access-token adapter."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.interface_adapters.exceptions.auth import AuthGatewayUnavailableError
from marquise.interface_adapters.readers import (
    JwtAccessTokenGateway,
    SigningKeyProvider,
)

ISSUER = "https://project.supabase.co/auth/v1"
AUDIENCE = "authenticated"


@pytest.mark.asyncio
async def test_jwt_gateway_delegates_to_provider_and_returns_plain_claims() -> None:
    """The adapter passes claim verification to its injected provider."""
    provider = create_autospec(SigningKeyProvider, instance=True)
    provider.verify.return_value = {"sub": "user-id", "app_metadata": {}}
    gateway = JwtAccessTokenGateway(provider, ISSUER, AUDIENCE)

    claims = await gateway.verify("encoded-token")

    assert claims == {"sub": "user-id", "app_metadata": {}}
    provider.verify.assert_called_once_with("encoded-token", ISSUER, AUDIENCE)


@pytest.mark.asyncio
async def test_jwt_gateway_preserves_signing_key_outage() -> None:
    """Provider availability failures remain distinguishable to the reader."""
    provider = create_autospec(SigningKeyProvider, instance=True)
    provider.verify.side_effect = AuthGatewayUnavailableError("JWKS unavailable")
    gateway = JwtAccessTokenGateway(provider, ISSUER, AUDIENCE)

    with pytest.raises(AuthGatewayUnavailableError, match="JWKS unavailable"):
        await gateway.verify("encoded-token")
