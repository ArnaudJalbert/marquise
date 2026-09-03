"""Tests for Account entity."""

from __future__ import annotations

import pytest

from marquise.domain.entities import Account
from marquise.domain.value_objects import MarquiseRole


def test_account_keeps_assigned_role() -> None:
    """Account stores its validated Marquise authorization role."""
    account = Account(
        id="account-id",
        email="user@example.com",
        role=MarquiseRole.EDITOR,
    )

    assert account.role is MarquiseRole.EDITOR


def test_account_allows_pending_role_assignment() -> None:
    """New invitation can exist briefly before protected metadata is assigned."""
    account = Account(id="account-id", email="user@example.com")

    assert account.role is None


@pytest.mark.parametrize(
    ("account_id", "email", "message"),
    [
        ("", "user@example.com", "id"),
        ("account-id", "", "email"),
    ],
)
def test_account_rejects_incomplete_identity(
    account_id: str,
    email: str,
    message: str,
) -> None:
    """Account requires a stable identifier and email address."""
    with pytest.raises(ValueError, match=message):
        Account(id=account_id, email=email)
