"""Tests for gateway-backed account repository."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import AuthAdministrationError
from marquise.domain.value_objects import MarquiseRole
from marquise.interface_adapters.repositories.account_repository import (
    GatewayAccountRepository,
)
from marquise.interface_adapters.repositories.protocols.auth import (
    AuthAdminGateway,
    AuthGatewayError,
)


@pytest.mark.asyncio
async def test_account_repository_maps_accounts_and_roles() -> None:
    """Admin gateway data and role values map across repository seam."""
    gateway = create_autospec(AuthAdminGateway, instance=True)
    gateway.invite.return_value = {"id": "user-id", "email": "user@example.com"}
    repository = GatewayAccountRepository(gateway)

    account = await repository.invite("user@example.com")
    await repository.set_role(account.id, MarquiseRole.ADMINISTRATOR)
    await repository.set_role(account.id, None)

    assert account.id == "user-id"
    gateway.set_role.assert_any_await("user-id", "administrator")
    gateway.set_role.assert_any_await("user-id", None)


@pytest.mark.asyncio
async def test_account_repository_keeps_invitation_provider_detail() -> None:
    """Invitation failures retain safe provider status and message for the CLI."""
    gateway = create_autospec(AuthAdminGateway, instance=True)
    gateway.invite.side_effect = AuthGatewayError(
        "Supabase Auth request failed (422): User already registered"
    )
    repository = GatewayAccountRepository(gateway)

    with pytest.raises(
        AuthAdministrationError,
        match=(
            r"Unable to invite account: Supabase Auth request failed \(422\): "
            "User already registered"
        ),
    ):
        await repository.invite("user@example.com")


@pytest.mark.asyncio
async def test_account_repository_hides_invalid_provider_data() -> None:
    """Malformed account payload becomes account-administration error."""
    gateway = create_autospec(AuthAdminGateway, instance=True)
    gateway.invite.return_value = {"id": "user-id"}
    repository = GatewayAccountRepository(gateway)

    with pytest.raises(AuthAdministrationError, match="invite"):
        await repository.invite("user@example.com")
