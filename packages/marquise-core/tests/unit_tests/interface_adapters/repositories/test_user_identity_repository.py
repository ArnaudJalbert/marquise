"""Tests for gateway-backed user identity repository."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import AuthAdministrationError
from marquise.domain.value_objects import MarquiseRole
from marquise.interface_adapters.repositories.protocols.auth import AuthAdminGateway
from marquise.interface_adapters.repositories.user_identity_repository import (
    GatewayUserIdentityRepository,
)


@pytest.mark.asyncio
async def test_user_identity_repository_maps_users_and_roles() -> None:
    """Admin gateway data and role values map across repository seam."""
    gateway = create_autospec(AuthAdminGateway, instance=True)
    gateway.invite.return_value = {"id": "user-id", "email": "user@example.com"}
    repository = GatewayUserIdentityRepository(gateway)

    user = await repository.invite("user@example.com")
    await repository.set_role(user.id, MarquiseRole.ADMINISTRATOR)
    await repository.set_role(user.id, None)

    assert user.id == "user-id"
    gateway.set_role.assert_any_await("user-id", "administrator")
    gateway.set_role.assert_any_await("user-id", None)


@pytest.mark.asyncio
async def test_user_identity_repository_hides_invalid_provider_data() -> None:
    """Malformed user payload becomes account-administration error."""
    gateway = create_autospec(AuthAdminGateway, instance=True)
    gateway.invite.return_value = {"id": "user-id"}
    repository = GatewayUserIdentityRepository(gateway)

    with pytest.raises(AuthAdministrationError, match="invite"):
        await repository.invite("user@example.com")
