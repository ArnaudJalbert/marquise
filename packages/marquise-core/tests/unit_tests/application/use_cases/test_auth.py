"""Tests for authentication and account-administration application logic."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    AccountNotFoundError,
    AuthAdministrationError,
    AuthorizationError,
    SelfDemotionError,
)
from marquise.application.readers import AccountIdentityReader
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


@pytest.mark.asyncio
async def test_authenticate_administrator_verifies_issued_token() -> None:
    """Password authentication is followed by shared identity reading."""
    passwords = create_autospec(PasswordAuthenticationRepository, instance=True)
    identities = create_autospec(AccountIdentityReader, instance=True)
    passwords.issue_access_token.return_value = "signed-token"
    identities.read.return_value = AccountIdentityReader.IdentityData(
        subject="admin-id", role="administrator"
    )
    use_case = AuthenticateAdministratorUseCase(passwords, identities)

    result = await use_case.execute(
        use_case.InputData(email="ADMIN@example.com", password="secret")
    )

    assert result.subject == "admin-id"
    passwords.issue_access_token.assert_awaited_once_with("admin@example.com", "secret")
    identities.read.assert_awaited_once_with("signed-token")


@pytest.mark.asyncio
async def test_authenticate_administrator_rejects_other_roles() -> None:
    """Valid Member credentials cannot authorize account administration."""
    passwords = create_autospec(PasswordAuthenticationRepository, instance=True)
    identities = create_autospec(AccountIdentityReader, instance=True)
    passwords.issue_access_token.return_value = "signed-token"
    identities.read.return_value = AccountIdentityReader.IdentityData(
        subject="member-id", role="member"
    )
    use_case = AuthenticateAdministratorUseCase(passwords, identities)

    with pytest.raises(AuthorizationError, match="Administrator"):
        await use_case.execute(
            use_case.InputData(email="member@example.com", password="secret")
        )


@pytest.mark.asyncio
async def test_invite_account_sets_role_metadata() -> None:
    """Invitation assigns selected protected role after account creation."""
    accounts = create_autospec(AccountRepository, instance=True)
    accounts.invite.return_value = Account(id="account-id", email="user@example.com")
    use_case = InviteAccountUseCase(accounts)

    result = await use_case.execute(
        use_case.InputData(email="USER@example.com", role="editor")
    )

    assert result == use_case.OutputData(
        account_id="account-id", email="user@example.com", role="editor"
    )
    accounts.invite.assert_awaited_once_with("user@example.com")
    accounts.set_role.assert_awaited_once_with("account-id", MarquiseRole.EDITOR)
    accounts.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_invite_account_rolls_back_failed_role_assignment() -> None:
    """Failed metadata assignment removes newly invited role-less account."""
    accounts = create_autospec(AccountRepository, instance=True)
    accounts.invite.return_value = Account(id="account-id", email="user@example.com")
    accounts.set_role.side_effect = AuthAdministrationError("provider failed")
    use_case = InviteAccountUseCase(accounts)

    with pytest.raises(AuthAdministrationError, match="provider failed"):
        await use_case.execute(
            use_case.InputData(email="user@example.com", role="member")
        )

    accounts.delete.assert_awaited_once_with("account-id")


@pytest.mark.asyncio
async def test_set_account_role_updates_other_account() -> None:
    """Administrator can clear another account's Marquise access."""
    accounts = create_autospec(AccountRepository, instance=True)
    accounts.find_by_email.return_value = Account(
        id="target-id", email="user@example.com"
    )
    use_case = SetAccountRoleUseCase(accounts)

    result = await use_case.execute(
        use_case.InputData(
            actor_account_id="admin-id", email="user@example.com", role=None
        )
    )

    assert result.role is None
    accounts.set_role.assert_awaited_once_with("target-id", None)


@pytest.mark.asyncio
async def test_set_account_role_blocks_self_demotion() -> None:
    """Administrator cannot clear or downgrade their own role."""
    accounts = create_autospec(AccountRepository, instance=True)
    accounts.find_by_email.return_value = Account(
        id="admin-id", email="admin@example.com"
    )
    use_case = SetAccountRoleUseCase(accounts)

    with pytest.raises(SelfDemotionError, match="own role"):
        await use_case.execute(
            use_case.InputData(
                actor_account_id="admin-id",
                email="admin@example.com",
                role="editor",
            )
        )

    accounts.set_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_account_role_rejects_unknown_email() -> None:
    """Unknown target email fails without attempting metadata update."""
    accounts = create_autospec(AccountRepository, instance=True)
    accounts.find_by_email.return_value = None
    use_case = SetAccountRoleUseCase(accounts)

    with pytest.raises(AccountNotFoundError, match="No account"):
        await use_case.execute(
            use_case.InputData(
                actor_account_id="admin-id",
                email="missing@example.com",
                role="member",
            )
        )

    accounts.set_role.assert_not_awaited()
