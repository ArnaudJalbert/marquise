"""Account managed by Marquise."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.domain.value_objects.marquise_role import MarquiseRole


@dataclass(kw_only=True, slots=True)
class Account:
    """Stable account identity and its assigned authorization role.

    A newly invited provider account may temporarily have no role while its
    protected application metadata is being assigned.
    """

    id: str
    email: str
    role: MarquiseRole | None = None

    def __post_init__(self) -> None:
        """Reject incomplete account records."""
        if not self.id:
            raise ValueError("account id must not be empty")
        if not self.email:
            raise ValueError("account email must not be empty")
