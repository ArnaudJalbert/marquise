"""Marquise authorization role."""

from __future__ import annotations

from enum import StrEnum


class MarquiseRole(StrEnum):
    """Fixed roles carried in trusted application metadata."""

    MEMBER = "member"
    EDITOR = "editor"
    ADMINISTRATOR = "administrator"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Return whether a string names a supported Marquise role."""
        return any(role.value == value for role in cls)

    def includes(self, required: MarquiseRole) -> bool:
        """Return whether this role includes the required authorization."""
        return self is required or (
            self is MarquiseRole.ADMINISTRATOR and required is MarquiseRole.EDITOR
        )
