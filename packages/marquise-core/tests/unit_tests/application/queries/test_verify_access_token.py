"""Tests for access-token verification query."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.queries import VerifyAccessTokenQuery
from marquise.application.readers import AccountIdentityReader


@pytest.mark.asyncio
async def test_verify_access_token_returns_delivery_dto() -> None:
    """Verified reader projection is copied into query output data."""
    identities = create_autospec(AccountIdentityReader, instance=True)
    identities.read.return_value = AccountIdentityReader.IdentityData(
        subject="admin-id",
        role="administrator",
    )
    query = VerifyAccessTokenQuery(identities)

    result = await query.execute(query.InputData(token="signed-token"))

    assert result == query.OutputData(
        subject="admin-id",
        role="administrator",
    )
    identities.read.assert_awaited_once_with("signed-token")


@pytest.mark.parametrize(
    ("role", "can_edit", "can_administer"),
    [
        ("member", False, False),
        ("editor", True, False),
        ("administrator", True, True),
    ],
)
def test_verified_identity_exposes_core_role_policy(
    role: str,
    can_edit: bool,
    can_administer: bool,
) -> None:
    """Delivery consumes core authorization decisions, not raw role strings."""
    caller = VerifyAccessTokenQuery.OutputData(subject="account-id", role=role)

    assert caller.can_edit is can_edit
    assert caller.can_administer is can_administer


def test_verify_access_token_rejects_empty_token() -> None:
    """Empty bearer token fails at query input boundary."""
    with pytest.raises(ValueError, match="token"):
        VerifyAccessTokenQuery.InputData(token="")
