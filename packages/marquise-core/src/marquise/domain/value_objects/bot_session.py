"""Transient credentials issued while creating a Bot account."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BotSession:
    """Anonymous account identity and its transient refresh token."""

    account_id: str
    refresh_token: str = field(repr=False)

    def __post_init__(self) -> None:
        """Reject incomplete session credentials."""
        if not self.account_id or not self.refresh_token:
            raise ValueError("Bot session requires an account ID and refresh token")
