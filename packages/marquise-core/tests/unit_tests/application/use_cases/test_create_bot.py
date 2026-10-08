"""Bot provisioning behavior through the application use case."""

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories.bot_repository import BotRepository
from marquise.application.use_cases.auth.authenticate_administrator import (
    AuthenticateAdministratorUseCase,
)
from marquise.application.use_cases.auth.create_bot import CreateBotUseCase
from marquise.domain.value_objects.bot_session import BotSession


@pytest.mark.asyncio
async def test_administrator_creates_editor_bot() -> None:
    """An authorized Administrator receives the new Bot's refresh token."""
    bots = create_autospec(BotRepository, instance=True)
    administrator = create_autospec(AuthenticateAdministratorUseCase, instance=True)
    administrator.InputData = AuthenticateAdministratorUseCase.InputData
    bots.identifier_exists.return_value = False
    bots.create_anonymous.return_value = BotSession(
        account_id="bot-account", refresh_token="one-time-secret"
    )
    result = await CreateBotUseCase(bots, administrator).execute(
        CreateBotUseCase.InputData("admin@example.com", "password", "pi.worker_2")
    )
    assert result.account_id == "bot-account"
    assert result.bot_id == "pi.worker_2"
    assert result.refresh_token == "one-time-secret"
    bots.assign_editor.assert_awaited_once_with("bot-account", "pi.worker_2")
    bots.delete.assert_not_awaited()
    assert "one-time-secret" not in repr(result)


@pytest.mark.asyncio
async def test_failed_metadata_assignment_deletes_new_account() -> None:
    """A failed role or identifier assignment leaves no new Bot account."""
    from marquise.application.exceptions.auth import AuthAdministrationError

    bots = create_autospec(BotRepository, instance=True)
    administrator = create_autospec(AuthenticateAdministratorUseCase, instance=True)
    administrator.InputData = AuthenticateAdministratorUseCase.InputData
    bots.identifier_exists.return_value = False
    bots.create_anonymous.return_value = BotSession(
        account_id="bot-account", refresh_token="secret"
    )
    bots.assign_editor.side_effect = AuthAdministrationError(
        "Provider rejected metadata"
    )
    with pytest.raises(AuthAdministrationError, match="Provider rejected metadata"):
        await CreateBotUseCase(bots, administrator).execute(
            CreateBotUseCase.InputData("admin@example.com", "password", "pi")
        )
    bots.delete.assert_awaited_once_with("bot-account")


@pytest.mark.parametrize(
    "bot_id", ["", "Pi", "pi worker", "pi/worker", "pi@worker", "pï", "pi\n"]
)
def test_invalid_bot_identifier_is_rejected(bot_id: str) -> None:
    """Bot Identifiers reject characters outside the approved lowercase set."""
    with pytest.raises(ValueError, match="Bot Identifier"):
        CreateBotUseCase.InputData("admin@example.com", "password", bot_id)


@pytest.mark.parametrize("bot_id", ["pi", "worker2", "pi.worker_2-archive", ".pi_-"])
def test_approved_bot_identifier_characters_are_accepted(bot_id: str) -> None:
    """Approved punctuation and lowercase alphanumeric characters are preserved."""
    assert (
        CreateBotUseCase.InputData("admin@example.com", "password", bot_id).bot_id
        == bot_id
    )


@pytest.mark.asyncio
async def test_duplicate_bot_identifier_is_rejected() -> None:
    """An existing identifier blocks creation regardless of the account role."""
    from marquise.application.exceptions.auth import AccountAlreadyExistsError

    bots = create_autospec(BotRepository, instance=True)
    administrator = create_autospec(AuthenticateAdministratorUseCase, instance=True)
    administrator.InputData = AuthenticateAdministratorUseCase.InputData
    bots.identifier_exists.return_value = True
    with pytest.raises(AccountAlreadyExistsError):
        await CreateBotUseCase(bots, administrator).execute(
            CreateBotUseCase.InputData("admin@example.com", "password", "pi")
        )
    bots.create_anonymous.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_administrator_cannot_use_privileged_operations() -> None:
    """Failed Administrator authorization prevents lookup and account creation."""
    from marquise.application.exceptions.auth import AuthorizationError

    bots = create_autospec(BotRepository, instance=True)
    administrator = create_autospec(AuthenticateAdministratorUseCase, instance=True)
    administrator.InputData = AuthenticateAdministratorUseCase.InputData
    administrator.execute.side_effect = AuthorizationError(
        "Administrator role required"
    )
    with pytest.raises(AuthorizationError):
        await CreateBotUseCase(bots, administrator).execute(
            CreateBotUseCase.InputData("admin@example.com", "password", "pi")
        )
    bots.identifier_exists.assert_not_awaited()
    bots.create_anonymous.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_failure_reports_account_without_token() -> None:
    """Failed cleanup reports the account requiring manual removal, never its token."""
    from marquise.application.exceptions.auth import AuthAdministrationError

    bots = create_autospec(BotRepository, instance=True)
    administrator = create_autospec(AuthenticateAdministratorUseCase, instance=True)
    administrator.InputData = AuthenticateAdministratorUseCase.InputData
    bots.identifier_exists.return_value = False
    bots.create_anonymous.return_value = BotSession(
        account_id="bot-account", refresh_token="secret"
    )
    bots.assign_editor.side_effect = AuthAdministrationError("setup failed")
    bots.delete.side_effect = AuthAdministrationError("delete failed")
    with pytest.raises(
        AuthAdministrationError, match="cleanup failed for account bot-account"
    ) as error:
        await CreateBotUseCase(bots, administrator).execute(
            CreateBotUseCase.InputData("admin@example.com", "password", "pi")
        )
    assert "secret" not in str(error.value)
