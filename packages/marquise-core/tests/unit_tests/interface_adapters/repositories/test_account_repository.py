"""Tests for gateway-backed account repository."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import AuthAdministrationError
from marquise.domain.value_objects import MarquiseRole
from marquise.interface_adapters.exceptions.auth import AuthGatewayError
from marquise.interface_adapters.repositories.account_repository import (
    GatewayAccountRepository,
)
from marquise.interface_adapters.repositories.protocols.auth import AuthAdminGateway


@pytest.mark.asyncio
async def test_account_repository_maps_accounts_and_roles() -> None:
    """Admin gateway data and role values map across repository seam."""
    gateway = create_autospec(AuthAdminGateway, instance=True)
    gateway.invite.return_value = {
        "id": "user-id",
        "email": "user@example.com",
        "app_metadata": {"marquise_role": "administrator"},
    }
    repository = GatewayAccountRepository(gateway)

    account = await repository.invite("user@example.com")
    await repository.set_role(account.id, MarquiseRole.ADMINISTRATOR)

    assert account.id == "user-id"
    assert account.role is MarquiseRole.ADMINISTRATOR
    gateway.set_role.assert_awaited_once_with("user-id", "administrator")


@pytest.mark.asyncio
async def test_account_repository_allows_pending_account_without_role() -> None:
    """Newly invited provider account may precede role metadata assignment."""
    gateway = create_autospec(AuthAdminGateway, instance=True)
    gateway.invite.return_value = {
        "id": "user-id",
        "email": "user@example.com",
    }
    repository = GatewayAccountRepository(gateway)

    account = await repository.invite("user@example.com")

    assert account.role is None


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
