"""Tests for gateway-backed password authentication repository."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    AuthenticationError,
    AuthenticationServiceUnavailableError,
)
from marquise.interface_adapters.exceptions.auth import (
    AuthGatewayError,
    AuthGatewayUnavailableError,
)
from marquise.interface_adapters.repositories.password_auth_repository import (
    GatewayPasswordAuthenticationRepository,
)
from marquise.interface_adapters.repositories.protocols.auth import PasswordAuthGateway


@pytest.mark.asyncio
async def test_password_repository_hides_gateway_failure() -> None:
    """Provider details do not escape failed password authentication."""
    gateway = create_autospec(PasswordAuthGateway, instance=True)
    gateway.issue_access_token.side_effect = AuthGatewayError("provider detail")
    repository = GatewayPasswordAuthenticationRepository(gateway)

    with pytest.raises(AuthenticationError, match="invalid"):
        await repository.issue_access_token("admin@example.com", "wrong")


@pytest.mark.asyncio
async def test_password_repository_preserves_provider_outage() -> None:
    """Provider outages remain distinguishable from invalid credentials."""
    gateway = create_autospec(PasswordAuthGateway, instance=True)
    gateway.issue_access_token.side_effect = AuthGatewayUnavailableError("offline")
    repository = GatewayPasswordAuthenticationRepository(gateway)

    with pytest.raises(AuthenticationServiceUnavailableError, match="unavailable"):
        await repository.issue_access_token("admin@example.com", "secret")
