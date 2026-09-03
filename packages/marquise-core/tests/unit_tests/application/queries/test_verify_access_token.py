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
        subject="admin-id", role="administrator"
    )
    query = VerifyAccessTokenQuery(identities)

    result = await query.execute(query.InputData(token="signed-token"))

    assert result == query.OutputData(subject="admin-id", role="administrator")
    identities.read.assert_awaited_once_with("signed-token")


def test_verify_access_token_rejects_empty_token() -> None:
    """Empty bearer token fails at query input boundary."""
    with pytest.raises(ValueError, match="token"):
        VerifyAccessTokenQuery.InputData(token="")
