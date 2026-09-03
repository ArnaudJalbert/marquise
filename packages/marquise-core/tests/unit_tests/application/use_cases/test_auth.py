"""Tests for authentication and account-administration application logic."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    AuthAdministrationError,
    AuthorizationError,
    SelfDemotionError,
)
from marquise.application.repositories import (
    AccountRepository,
    PasswordAuthenticationRepository,
)
from marquise.application.use_cases import (
    AuthenticateAdministratorUseCase,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
)
from marquise.domain.entities import Account
from marquise.domain.value_objects import MarquiseRole


def _administrator_authentication(
    subject: str = "admin-id",
) -> AuthenticateAdministratorUseCase:
    authentication = create_autospec(
        AuthenticateAdministratorUseCase,
        instance=True,
    )
    authentication.InputData = AuthenticateAdministratorUseCase.InputData
    authentication.execute.return_value = AuthenticateAdministratorUseCase.OutputData(
        subject=subject
    )
    return authentication


@pytest.mark.asyncio
async def test_authenticate_administrator_verifies_issued_token() -> None:
    """Password authentication is followed by shared identity reading."""
    passwords = create_autospec(PasswordAuthenticationRepository, instance=True)
    identities = create_autospec(AccountIdentityReader, instance=True)
    passwords.issue_access_token.return_value = "signed-token"
    identities.read.return_value = AccountIdentityReader.IdentityData(
        subject="admin-id",
        role="administrator",
    )
    use_case = AuthenticateAdministratorUseCase(passwords, identities)

    result = await use_case.execute(
        use_case.InputData(email="ADMIN@example.com", password="secret")
    )

    assert result.subject == "admin-id"
    passwords.issue_access_token.assert_awaited_once_with(
        "admin@example.com",
        "secret",
    )
    identities.read.assert_awaited_once_with("signed-token")


@pytest.mark.asyncio
async def test_authenticate_administrator_rejects_other_roles() -> None:
    """Valid Member credentials cannot authorize account administration."""
    passwords = create_autospec(PasswordAuthenticationRepository, instance=True)
    identities = create_autospec(AccountIdentityReader, instance=True)
    passwords.issue_access_token.return_value = "signed-token"
    identities.read.return_value = AccountIdentityReader.IdentityData(
        subject="member-id",
        role="member",
    )
    use_case = AuthenticateAdministratorUseCase(passwords, identities)

    with pytest.raises(AuthorizationError, match="Administrator"):
        await use_case.execute(
            use_case.InputData(email="member@example.com", password="secret")
        )


@pytest.mark.asyncio
async def test_invite_account_authenticates_and_sets_role_metadata() -> None:
    """Invitation authorizes its actor and assigns protected role metadata."""
    accounts = create_autospec(AccountRepository, instance=True)
    authentication = _administrator_authentication()
    accounts.find_by_email.return_value = None
    accounts.invite.return_value = Account(
        id="account-id",
        email="user@example.com",
    )
    use_case = InviteAccountUseCase(accounts, authentication)

    result = await use_case.execute(
        use_case.InputData(
            administrator_email="ADMIN@example.com",
            administrator_password="secret",
            email="USER@example.com",
            role="editor",
        )
    )

    assert result == use_case.OutputData(
        account_id="account-id",
        email="user@example.com",
        role="editor",
    )
    authentication.execute.assert_awaited_once_with(
        authentication.InputData(
            email="admin@example.com",
            password="secret",
        )
    )
    accounts.find_by_email.assert_awaited_once_with("user@example.com")
    accounts.invite.assert_awaited_once_with("user@example.com")
    accounts.set_role.assert_awaited_once_with(
        "account-id",
        MarquiseRole.EDITOR,
    )


@pytest.mark.asyncio
async def test_invite_account_rejects_existing_account_without_mutation() -> None:
    """A pre-existing pending account is never invited, changed, or deleted."""
    accounts = create_autospec(AccountRepository, instance=True)
    authentication = _administrator_authentication()
    accounts.find_by_email.return_value = Account(
        id="existing-id",
        email="user@example.com",
    )
    use_case = InviteAccountUseCase(accounts, authentication)

    with pytest.raises(AccountAlreadyExistsError, match="already exists"):
        await use_case.execute(
            use_case.InputData(
                administrator_email="admin@example.com",
                administrator_password="secret",
                email="user@example.com",
                role="member",
            )
        )

    accounts.invite.assert_not_awaited()
    accounts.set_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_invite_account_never_deletes_after_role_failure() -> None:
    """Failed role assignment leaves the new account for safe remediation."""
    accounts = create_autospec(AccountRepository, instance=True)
    authentication = _administrator_authentication()
    accounts.find_by_email.return_value = None
    accounts.invite.return_value = Account(
        id="account-id",
        email="user@example.com",
    )
    accounts.set_role.side_effect = AuthAdministrationError("provider failed")
    use_case = InviteAccountUseCase(accounts, authentication)

    with pytest.raises(AuthAdministrationError, match="provider failed"):
        await use_case.execute(
            use_case.InputData(
                administrator_email="admin@example.com",
                administrator_password="secret",
                email="user@example.com",
                role="member",
            )
        )

    accounts.invite.assert_awaited_once_with("user@example.com")
    accounts.set_role.assert_awaited_once_with(
        "account-id",
        MarquiseRole.MEMBER,
    )
    assert not hasattr(accounts, "delete")


@pytest.mark.asyncio
async def test_invite_account_stops_when_actor_is_not_administrator() -> None:
    """Unauthorized credentials fail before target account lookup."""
    accounts = create_autospec(AccountRepository, instance=True)
    authentication = _administrator_authentication()
    authentication.execute.side_effect = AuthorizationError(
        "Administrator role required"
    )
    use_case = InviteAccountUseCase(accounts, authentication)

    with pytest.raises(AuthorizationError, match="Administrator"):
        await use_case.execute(
            use_case.InputData(
                administrator_email="member@example.com",
                administrator_password="secret",
                email="user@example.com",
                role="member",
            )
        )

    accounts.find_by_email.assert_not_awaited()
    accounts.invite.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_account_role_updates_other_account() -> None:
    """Administrator can assign one of the supported roles to another account."""
    accounts = create_autospec(AccountRepository, instance=True)
    authentication = _administrator_authentication()
    accounts.find_by_email.return_value = Account(
        id="target-id",
        email="user@example.com",
    )
    use_case = SetAccountRoleUseCase(accounts, authentication)

    result = await use_case.execute(
        use_case.InputData(
            administrator_email="admin@example.com",
            administrator_password="secret",
            email="user@example.com",
            role="editor",
        )
    )

    assert result.role == "editor"
    accounts.set_role.assert_awaited_once_with(
        "target-id",
        MarquiseRole.EDITOR,
    )


@pytest.mark.asyncio
async def test_set_account_role_blocks_self_demotion() -> None:
    """Administrator cannot downgrade their own role."""
    accounts = create_autospec(AccountRepository, instance=True)
    authentication = _administrator_authentication()
    accounts.find_by_email.return_value = Account(
        id="admin-id",
        email="admin@example.com",
    )
    use_case = SetAccountRoleUseCase(accounts, authentication)

    with pytest.raises(SelfDemotionError, match="own Administrator"):
        await use_case.execute(
            use_case.InputData(
                administrator_email="admin@example.com",
                administrator_password="secret",
                email="admin@example.com",
                role="editor",
            )
        )

    accounts.set_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_account_role_rejects_unknown_email() -> None:
    """Unknown target email fails without attempting metadata update."""
    accounts = create_autospec(AccountRepository, instance=True)
    authentication = _administrator_authentication()
    accounts.find_by_email.return_value = None
    use_case = SetAccountRoleUseCase(accounts, authentication)

    with pytest.raises(AccountNotFoundError, match="No account"):
        await use_case.execute(
            use_case.InputData(
                administrator_email="admin@example.com",
                administrator_password="secret",
                email="missing@example.com",
                role="member",
            )
        )

    accounts.set_role.assert_not_awaited()
