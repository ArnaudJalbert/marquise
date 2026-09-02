"""Tests for Administrator-authenticated account commands."""

from __future__ import annotations

from unittest.mock import create_autospec, patch

import pytest

from marquise import (
    AuthenticateAdministratorUseCase,
    AuthenticationError,
    AuthFactory,
    AuthorizationError,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
)
from marquise_cli.auth_commands import (
    AuthSettings,
    _administrator_credentials,
    invite,
    load_auth_settings,
    run_invite,
    run_login,
    run_set_role,
)


def test_load_auth_settings_requires_only_supabase_auth_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auth administration does not require database configuration."""
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co/")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert load_auth_settings() == AuthSettings(
        supabase_url="https://project.supabase.co",
        publishable_key="publishable",
        service_role_key="service",
    )


def test_configured_administrator_credentials_avoid_prompts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Complete configured credentials avoid interactive input."""
    monkeypatch.setenv("MARQUISE_EMAIL", "admin@example.com")
    monkeypatch.setenv("MARQUISE_PASSWORD", "secret")

    with (
        patch("builtins.input") as input_prompt,
        patch("marquise_cli.auth_commands.prompt_password") as password_prompt,
    ):
        assert _administrator_credentials() == ("admin@example.com", "secret")

    input_prompt.assert_not_called()
    password_prompt.assert_not_called()


def test_incomplete_administrator_credentials_prompt_for_both(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Partial environment configuration does not mix credential sources."""
    monkeypatch.setenv("MARQUISE_EMAIL", "configured@example.com")
    monkeypatch.delenv("MARQUISE_PASSWORD", raising=False)

    with (
        patch("builtins.input", return_value="prompted@example.com"),
        patch(
            "marquise_cli.auth_commands.prompt_password", return_value="prompted-secret"
        ),
    ):
        assert _administrator_credentials() == (
            "prompted@example.com",
            "prompted-secret",
        )


def _factory() -> tuple[
    AuthFactory,
    AuthenticateAdministratorUseCase,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
]:
    factory = create_autospec(AuthFactory, instance=True)
    authenticate = create_autospec(AuthenticateAdministratorUseCase, instance=True)
    authenticate.InputData = AuthenticateAdministratorUseCase.InputData
    authenticate.execute.return_value = AuthenticateAdministratorUseCase.OutputData(
        subject="admin-id"
    )
    invite = create_autospec(InviteAccountUseCase, instance=True)
    invite.InputData = InviteAccountUseCase.InputData
    invite.execute.return_value = InviteAccountUseCase.OutputData(
        account_id="account-id", email="user@example.com", role="editor"
    )
    set_role = create_autospec(SetAccountRoleUseCase, instance=True)
    set_role.InputData = SetAccountRoleUseCase.InputData
    set_role.execute.return_value = SetAccountRoleUseCase.OutputData(
        account_id="account-id", email="user@example.com", role=None
    )
    factory.authenticate_administrator_use_case = authenticate
    factory.invite_account_use_case = invite
    factory.set_account_role_use_case = set_role
    return factory, authenticate, invite, set_role


@pytest.mark.asyncio
async def test_invite_authenticates_before_invitation() -> None:
    """CLI verifies Administrator before invoking invitation use case."""
    factory, authenticate, invite, _ = _factory()

    await run_invite(
        factory,
        administrator_email="admin@example.com",
        administrator_password="secret",
        email="user@example.com",
        role="editor",
    )

    authenticate.execute.assert_awaited_once()
    invite.execute.assert_awaited_once_with(
        InviteAccountUseCase.InputData(email="user@example.com", role="editor")
    )


@pytest.mark.asyncio
async def test_invite_stops_when_caller_is_not_administrator() -> None:
    """Failed Administrator authorization prevents privileged invitation."""
    factory, authenticate, invite, _ = _factory()
    authenticate.execute.side_effect = AuthorizationError("Administrator required")

    with pytest.raises(AuthorizationError):
        await run_invite(
            factory,
            administrator_email="member@example.com",
            administrator_password="secret",
            email="user@example.com",
            role="member",
        )

    invite.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_authenticates_administrator(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Login confirms that supplied credentials have Administrator access."""
    factory, authenticate, _, _ = _factory()

    await run_login(
        factory,
        administrator_email="admin@example.com",
        administrator_password="secret",
    )

    authenticate.execute.assert_awaited_once()
    assert capsys.readouterr().out == "Authenticated as Administrator.\n"


def test_invite_labels_administrator_authentication_failure(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Credential failures identify Administrator authentication, not invitation."""
    monkeypatch.setattr(
        "marquise_cli.auth_commands.load_auth_settings",
        lambda: AuthSettings("https://project.supabase.co", "key", "service"),
    )
    monkeypatch.setattr(
        "marquise_cli.auth_commands._administrator_credentials",
        lambda: ("admin@example.com", "secret"),
    )
    factory, authenticate, _, _ = _factory()
    authenticate.execute.side_effect = AuthenticationError(
        "Email or password is invalid"
    )
    monkeypatch.setattr("marquise_cli.auth_commands._factory", lambda _: factory)

    with pytest.raises(SystemExit) as error:
        invite("user@example.com", "editor")

    assert error.value.code == 1
    assert (
        capsys.readouterr().err
        == "Failed to authenticate Administrator: Email or password is invalid\n"
    )


@pytest.mark.asyncio
async def test_set_role_passes_authenticated_actor_identity() -> None:
    """Role update receives actor ID needed for self-demotion protection."""
    factory, authenticate, _, set_role = _factory()

    await run_set_role(
        factory,
        administrator_email="admin@example.com",
        administrator_password="secret",
        email="user@example.com",
        role=None,
    )

    authenticate.execute.assert_awaited_once()
    set_role.execute.assert_awaited_once_with(
        SetAccountRoleUseCase.InputData(
            actor_account_id="admin-id",
            email="user@example.com",
            role=None,
        )
    )
