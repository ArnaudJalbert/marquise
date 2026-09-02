"""Tests for gateway-backed account identity reader."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import AuthenticationError
from marquise.interface_adapters.readers import GatewayAccountIdentityReader
from marquise.interface_adapters.repositories.protocols.auth import AccessTokenGateway


@pytest.mark.asyncio
async def test_account_identity_reader_maps_required_claims() -> None:
    """Verified gateway claims become minimal identity read data."""
    gateway = create_autospec(AccessTokenGateway, instance=True)
    gateway.verify.return_value = {
        "sub": "user-id",
        "app_metadata": {"marquise_role": "editor"},
    }
    reader = GatewayAccountIdentityReader(gateway)

    identity = await reader.read("token")

    assert identity.subject == "user-id"
    assert identity.role == "editor"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "user-id"},
        {"sub": "user-id", "app_metadata": {"marquise_role": "owner"}},
        {"sub": "", "app_metadata": {"marquise_role": "member"}},
    ],
)
async def test_account_identity_reader_rejects_invalid_claims(
    claims: dict,
) -> None:
    """Missing, unknown, and empty identity claims cannot authenticate."""
    gateway = create_autospec(AccessTokenGateway, instance=True)
    gateway.verify.return_value = claims
    reader = GatewayAccountIdentityReader(gateway)

    with pytest.raises(AuthenticationError):
        await reader.read("token")
