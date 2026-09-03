"""Marquise authorization role."""

from __future__ import annotations

from enum import StrEnum


class MarquiseRole(StrEnum):
    """Fixed roles carried in trusted Supabase application metadata."""

    MEMBER = "member"
    EDITOR = "editor"
    ADMINISTRATOR = "administrator"

    def includes(self, required: MarquiseRole) -> bool:
        """Return whether this role includes the required authorization."""
        return self is required or (
            self is MarquiseRole.ADMINISTRATOR and required is MarquiseRole.EDITOR
        )
