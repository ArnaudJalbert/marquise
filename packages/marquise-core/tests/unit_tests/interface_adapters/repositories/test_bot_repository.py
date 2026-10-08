"""Bot credentials and metadata at the provider adapter boundary."""

from unittest.mock import create_autospec

import pytest

from marquise.interface_adapters.repositories.bot_repository import GatewayBotRepository
from marquise.interface_adapters.repositories.protocols.auth import BotAuthGateway


@pytest.mark.asyncio
async def test_bot_session_and_editor_metadata() -> None:
    """Provider credentials map to a transient session and protected Bot claims."""
    gateway = create_autospec(BotAuthGateway, instance=True)
    gateway.create_anonymous.return_value = {
        "user": {"id": "new-bot"},
        "refresh_token": "secret",
    }
    repository = GatewayBotRepository(gateway)
    session = await repository.create_anonymous()
    assert session.account_id == "new-bot"
    assert session.refresh_token == "secret"
    await repository.assign_editor(session.account_id, "pi.worker_2")
    gateway.assign_editor.assert_awaited_once_with("new-bot", "pi.worker_2")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", ["identifier_exists", "create_anonymous", "assign_editor", "delete"]
)
async def test_provider_failures_do_not_expose_secrets(operation: str) -> None:
    """Provider errors cannot expose credentials in application messages."""
    from marquise.application.exceptions.auth import AuthAdministrationError
    from marquise.interface_adapters.exceptions.auth import AuthGatewayError

    gateway = create_autospec(BotAuthGateway, instance=True)
    getattr(gateway, operation).side_effect = AuthGatewayError("credential-secret")
    repository = GatewayBotRepository(gateway)
    arguments = {
        "identifier_exists": ("pi",),
        "create_anonymous": (),
        "assign_editor": ("account-id", "pi"),
        "delete": ("account-id",),
    }
    with pytest.raises(AuthAdministrationError) as error:
        await getattr(repository, operation)(*arguments[operation])
    assert "credential-secret" not in str(error.value)


@pytest.mark.asyncio
async def test_missing_refresh_token_deletes_created_account() -> None:
    """A malformed session response with a known account ID triggers cleanup."""
    from marquise.application.exceptions.auth import AuthAdministrationError

    gateway = create_autospec(BotAuthGateway, instance=True)
    gateway.create_anonymous.return_value = {"user": {"id": "new-bot"}}
    with pytest.raises(AuthAdministrationError, match="no refresh token"):
        await GatewayBotRepository(gateway).create_anonymous()
    gateway.delete.assert_awaited_once_with("new-bot")
