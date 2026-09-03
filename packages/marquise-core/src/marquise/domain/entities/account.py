"""Account managed by Marquise."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class Account:
    """Stable account identifier and email address."""

    id: str
    email: str

    def __post_init__(self) -> None:
        """Reject incomplete account records."""
        if not self.id:
            raise ValueError("account id must not be empty")
        if not self.email:
            raise ValueError("account email must not be empty")
