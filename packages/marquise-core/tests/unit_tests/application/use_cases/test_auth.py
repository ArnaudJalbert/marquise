"""Tests for authentication and account-administration application logic."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    AuthAdministrationError,
    AuthorizationError,
    AuthUserNotFoundError,
    SelfDemotionError,
)
from marquise.application.readers import UserIdentityReader
from marquise.application.repositories import (
    PasswordAuthenticationRepository,
    UserIdentityRepository,
)
from marquise.application.use_cases import (
    AuthenticateAdministratorUseCase,
    InviteAuthUserUseCase,
    SetAuthUserRoleUseCase,
)
from marquise.domain.entities import UserIdentity
from marquise.domain.value_objects import MarquiseRole


@pytest.mark.asyncio
async def test_authenticate_administrator_verifies_issued_token() -> None:
    """Password authentication is followed by shared identity reading."""
    passwords = create_autospec(PasswordAuthenticationRepository, instance=True)
    identities = create_autospec(UserIdentityReader, instance=True)
    passwords.issue_access_token.return_value = "signed-token"
    identities.read.return_value = UserIdentityReader.IdentityData(
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
    identities = create_autospec(UserIdentityReader, instance=True)
    passwords.issue_access_token.return_value = "signed-token"
    identities.read.return_value = UserIdentityReader.IdentityData(
        subject="member-id", role="member"
    )
    use_case = AuthenticateAdministratorUseCase(passwords, identities)

    with pytest.raises(AuthorizationError, match="Administrator"):
        await use_case.execute(
            use_case.InputData(email="member@example.com", password="secret")
        )


@pytest.mark.asyncio
async def test_invite_user_sets_role_metadata() -> None:
    """Invitation assigns selected protected role after user creation."""
    users = create_autospec(UserIdentityRepository, instance=True)
    users.invite.return_value = UserIdentity(id="user-id", email="user@example.com")
    use_case = InviteAuthUserUseCase(users)

    result = await use_case.execute(
        use_case.InputData(email="USER@example.com", role="editor")
    )

    assert result == use_case.OutputData(
        user_id="user-id", email="user@example.com", role="editor"
    )
    users.invite.assert_awaited_once_with("user@example.com")
    users.set_role.assert_awaited_once_with("user-id", MarquiseRole.EDITOR)
    users.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_invite_user_rolls_back_failed_role_assignment() -> None:
    """Failed metadata assignment removes newly invited role-less account."""
    users = create_autospec(UserIdentityRepository, instance=True)
    users.invite.return_value = UserIdentity(id="user-id", email="user@example.com")
    users.set_role.side_effect = AuthAdministrationError("provider failed")
    use_case = InviteAuthUserUseCase(users)

    with pytest.raises(AuthAdministrationError, match="provider failed"):
        await use_case.execute(
            use_case.InputData(email="user@example.com", role="member")
        )

    users.delete.assert_awaited_once_with("user-id")


@pytest.mark.asyncio
async def test_set_user_role_updates_other_account() -> None:
    """Administrator can clear another account's Marquise access."""
    users = create_autospec(UserIdentityRepository, instance=True)
    users.find_by_email.return_value = UserIdentity(
        id="target-id", email="user@example.com"
    )
    use_case = SetAuthUserRoleUseCase(users)

    result = await use_case.execute(
        use_case.InputData(
            actor_user_id="admin-id", email="user@example.com", role=None
        )
    )

    assert result.role is None
    users.set_role.assert_awaited_once_with("target-id", None)


@pytest.mark.asyncio
async def test_set_user_role_blocks_self_demotion() -> None:
    """Administrator cannot clear or downgrade their own role."""
    users = create_autospec(UserIdentityRepository, instance=True)
    users.find_by_email.return_value = UserIdentity(
        id="admin-id", email="admin@example.com"
    )
    use_case = SetAuthUserRoleUseCase(users)

    with pytest.raises(SelfDemotionError, match="own role"):
        await use_case.execute(
            use_case.InputData(
                actor_user_id="admin-id",
                email="admin@example.com",
                role="editor",
            )
        )

    users.set_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_user_role_rejects_unknown_email() -> None:
    """Unknown target email fails without attempting metadata update."""
    users = create_autospec(UserIdentityRepository, instance=True)
    users.find_by_email.return_value = None
    use_case = SetAuthUserRoleUseCase(users)

    with pytest.raises(AuthUserNotFoundError, match="No user"):
        await use_case.execute(
            use_case.InputData(
                actor_user_id="admin-id",
                email="missing@example.com",
                role="member",
            )
        )

    users.set_role.assert_not_awaited()
