"""User identity managed by Marquise."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class UserIdentity:
    """Stable user identifier and email address."""

    id: str
    email: str

    def __post_init__(self) -> None:
        """Reject incomplete user records."""
        if not self.id:
            raise ValueError("user id must not be empty")
        if not self.email:
            raise ValueError("user email must not be empty")
