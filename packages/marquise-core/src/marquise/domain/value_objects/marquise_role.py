"""Marquise authorization role."""

from __future__ import annotations

from enum import StrEnum


class MarquiseRole(StrEnum):
    """Fixed roles carried in trusted Supabase application metadata."""

    MEMBER = "member"
    EDITOR = "editor"
    ADMINISTRATOR = "administrator"
