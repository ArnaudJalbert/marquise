"""Tests for MarquiseRole value object."""

from __future__ import annotations

import pytest

from marquise.domain.value_objects import MarquiseRole


@pytest.mark.parametrize(
    "value",
    ["member", "editor", "administrator"],
)
def test_role_validation_accepts_supported_values(value: str) -> None:
    """Role validation recognizes every supported external value."""
    assert MarquiseRole.is_valid(value)


def test_role_validation_rejects_unknown_value() -> None:
    """Role validation rejects values outside the fixed authorization model."""
    assert not MarquiseRole.is_valid("owner")


@pytest.mark.parametrize(
    ("role", "required", "included"),
    [
        (MarquiseRole.MEMBER, MarquiseRole.EDITOR, False),
        (MarquiseRole.EDITOR, MarquiseRole.EDITOR, True),
        (MarquiseRole.ADMINISTRATOR, MarquiseRole.EDITOR, True),
        (MarquiseRole.ADMINISTRATOR, MarquiseRole.ADMINISTRATOR, True),
    ],
)
def test_role_hierarchy(
    role: MarquiseRole,
    required: MarquiseRole,
    included: bool,
) -> None:
    """Administrator inherits Editor authorization and no broader hierarchy."""
    assert role.includes(required) is included
