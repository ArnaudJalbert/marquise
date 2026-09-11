"""Tests for Administrator-authenticated account commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import create_autospec, patch

import pytest

from marquise import (
    AccountNotFoundError,
    AuthAdministrationError,
    AuthenticationError,
    AuthorizationError,
    InviteAccountUseCase,
    MarquiseFactory,
    SetAccountRoleUseCase,
)
from marquise_cli.auth_commands import (
    _administrator_credentials,
    invite,
    run_invite,
    run_set_role,
    set_role,
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
            "marquise_cli.auth_commands.prompt_password",
            return_value="prompted-secret",
        ),
    ):
        assert _administrator_credentials() == (
            "prompted@example.com",
            "prompted-secret",
        )


@pytest.mark.parametrize(
    "command",
    [invite, set_role],
)
@pytest.mark.parametrize(
    ("expected_status", "prompt_error", "expected_error"),
    [
        (
            1,
            EOFError(),
            "Failed to read Administrator credentials: "
            "Interactive input is unavailable. "
            "Set both MARQUISE_EMAIL and MARQUISE_PASSWORD for noninteractive use.\n",
        ),
        (
            130,
            KeyboardInterrupt(),
            "Administrator credential entry cancelled.\n",
        ),
    ],
)
def test_commands_handle_unavailable_or_cancelled_credential_input(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command: Callable[[str, str], None],
    expected_status: int,
    prompt_error: BaseException,
    expected_error: str,
) -> None:
    """Credential prompt failures exit cleanly before factory construction."""
    monkeypatch.delenv("MARQUISE_EMAIL", raising=False)
    monkeypatch.delenv("MARQUISE_PASSWORD", raising=False)

    with (
        patch("builtins.input", side_effect=prompt_error),
        patch("marquise_cli.auth_commands.MarquiseFactory") as factory,
    ):
        with pytest.raises(SystemExit) as error:
            command("user@example.com", "editor")

    assert error.value.code == expected_status
    assert capsys.readouterr().err == expected_error
    factory.assert_not_called()


@pytest.mark.parametrize("command", [invite, set_role])
def test_commands_handle_cancelled_password_prompt(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command: Callable[[str, str], None],
) -> None:
    """Cancelling the password prompt exits before factory construction."""
    monkeypatch.delenv("MARQUISE_EMAIL", raising=False)
    monkeypatch.delenv("MARQUISE_PASSWORD", raising=False)

    with (
        patch("builtins.input", return_value="admin@example.com"),
        patch("marquise_cli.auth_commands.prompt_password", return_value=""),
        patch("marquise_cli.auth_commands.MarquiseFactory") as factory,
    ):
        with pytest.raises(SystemExit) as error:
            command("user@example.com", "editor")

    assert error.value.code == 130
    assert capsys.readouterr().err == "Administrator credential entry cancelled.\n"
    factory.assert_not_called()


@pytest.mark.parametrize("command", [invite, set_role])
def test_commands_handle_interrupted_password_prompt(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command: Callable[[str, str], None],
) -> None:
    """Interrupting the password prompt exits before factory construction."""
    monkeypatch.delenv("MARQUISE_EMAIL", raising=False)
    monkeypatch.delenv("MARQUISE_PASSWORD", raising=False)

    with (
        patch("builtins.input", return_value="admin@example.com"),
        patch(
            "marquise_cli.auth_commands.prompt_password",
            side_effect=KeyboardInterrupt(),
        ),
        patch("marquise_cli.auth_commands.MarquiseFactory") as factory,
    ):
        with pytest.raises(SystemExit) as error:
            command("user@example.com", "editor")

    assert error.value.code == 130
    assert capsys.readouterr().err == "Administrator credential entry cancelled.\n"
    factory.assert_not_called()


def _mock_factory() -> tuple[
    MarquiseFactory,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
]:
    factory = create_autospec(MarquiseFactory, instance=True)
    invite_use_case = create_autospec(InviteAccountUseCase, instance=True)
    invite_use_case.InputData = InviteAccountUseCase.InputData
    invite_use_case.execute.return_value = InviteAccountUseCase.OutputData(
        account_id="account-id",
        email="user@example.com",
        role="editor",
    )
    set_role_use_case = create_autospec(SetAccountRoleUseCase, instance=True)
    set_role_use_case.InputData = SetAccountRoleUseCase.InputData
    set_role_use_case.execute.return_value = SetAccountRoleUseCase.OutputData(
        account_id="account-id",
        email="user@example.com",
        role="editor",
    )
    factory.invite_account_use_case = invite_use_case
    factory.set_account_role_use_case = set_role_use_case
    return factory, invite_use_case, set_role_use_case


def _configure_command(
    monkeypatch: pytest.MonkeyPatch,
    factory: MarquiseFactory,
) -> None:
    monkeypatch.setattr(
        "marquise_cli.auth_commands._administrator_credentials",
        lambda: ("admin@example.com", "secret"),
    )
    monkeypatch.setattr(
        "marquise_cli.auth_commands.MarquiseFactory",
        lambda: factory,
    )


@pytest.mark.asyncio
async def test_invite_executes_one_authorized_workflow(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI passes actor credentials and target data to one application use case."""
    factory, invite_use_case, _ = _mock_factory()

    await run_invite(
        factory,
        administrator_email="admin@example.com",
        administrator_password="secret",
        email="user@example.com",
        role="editor",
    )

    invite_use_case.execute.assert_awaited_once_with(
        InviteAccountUseCase.InputData(
            administrator_email="admin@example.com",
            administrator_password="secret",
            email="user@example.com",
            role="editor",
        )
    )
    assert capsys.readouterr().out == (
        'Invited account "user@example.com" as editor.\n'
    )


@pytest.mark.asyncio
async def test_invite_propagates_non_administrator_failure() -> None:
    """A rejected actor is surfaced by the single authorized workflow."""
    factory, invite_use_case, _ = _mock_factory()
    invite_use_case.execute.side_effect = AuthorizationError(
        "Administrator role required"
    )

    with pytest.raises(AuthorizationError, match="Administrator"):
        await run_invite(
            factory,
            administrator_email="member@example.com",
            administrator_password="secret",
            email="user@example.com",
            role="member",
        )


def test_invite_labels_administrator_authentication_failure(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Credential failures identify Administrator authentication."""
    factory, invite_use_case, _ = _mock_factory()
    invite_use_case.execute.side_effect = AuthenticationError(
        "Email or password is invalid"
    )
    _configure_command(monkeypatch, factory)

    with pytest.raises(SystemExit) as error:
        invite("user@example.com", "editor")

    assert error.value.code == 1
    assert capsys.readouterr().err == (
        "Failed to authenticate Administrator: Email or password is invalid\n"
    )


def test_invite_reports_provider_failure(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invitation provider failures are labeled as account failures."""
    factory, invite_use_case, _ = _mock_factory()
    invite_use_case.execute.side_effect = AuthAdministrationError("provider failed")
    _configure_command(monkeypatch, factory)

    with pytest.raises(SystemExit) as error:
        invite("user@example.com", "member")

    assert error.value.code == 1
    assert capsys.readouterr().err == ("Failed to invite account: provider failed\n")


@pytest.mark.asyncio
async def test_set_role_executes_one_authorized_workflow(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A valid role update includes Administrator credentials and target data."""
    factory, _, set_role_use_case = _mock_factory()

    await run_set_role(
        factory,
        administrator_email="admin@example.com",
        administrator_password="secret",
        email="user@example.com",
        role="editor",
    )

    set_role_use_case.execute.assert_awaited_once_with(
        SetAccountRoleUseCase.InputData(
            administrator_email="admin@example.com",
            administrator_password="secret",
            email="user@example.com",
            role="editor",
        )
    )
    assert capsys.readouterr().out == (
        'Updated account "user@example.com" role to editor.\n'
    )


def test_set_role_reports_non_administrator(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-Administrator cannot run account role changes."""
    factory, _, set_role_use_case = _mock_factory()
    set_role_use_case.execute.side_effect = AuthorizationError(
        "Administrator role required"
    )
    _configure_command(monkeypatch, factory)

    with pytest.raises(SystemExit) as error:
        set_role("user@example.com", "editor")

    assert error.value.code == 1
    assert capsys.readouterr().err == (
        "Failed to authenticate Administrator: Administrator role required\n"
    )


def test_set_role_reports_unknown_account(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unknown target account receives a clear command failure."""
    factory, _, set_role_use_case = _mock_factory()
    set_role_use_case.execute.side_effect = AccountNotFoundError("No account found")
    _configure_command(monkeypatch, factory)

    with pytest.raises(SystemExit) as error:
        set_role("missing@example.com", "member")

    assert error.value.code == 1
    assert capsys.readouterr().err == (
        "Failed to update account role: No account found\n"
    )


def test_set_role_reports_provider_failure(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider failure is surfaced without hiding the safe detail."""
    factory, _, set_role_use_case = _mock_factory()
    set_role_use_case.execute.side_effect = AuthAdministrationError("provider failed")
    _configure_command(monkeypatch, factory)

    with pytest.raises(SystemExit) as error:
        set_role("user@example.com", "administrator")

    assert error.value.code == 1
    assert capsys.readouterr().err == (
        "Failed to update account role: provider failed\n"
    )
