"""Verify a bearer access token."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.readers.account_identity_reader import (
    AccountIdentityReader,
)


class VerifyAccessTokenQuery:
    """Return trusted identity data for a verified access token."""

    # noinspection package-requirements
    @dataclass(frozen=True, slots=True)
    class InputData:
        """Encoded bearer token to verify."""

        token: str

        def __post_init__(self) -> None:
            """Reject empty tokens."""
            if not self.token:
                raise ValueError("token must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Trusted caller identity exposed to delivery."""

        subject: str
        role: str

    def __init__(self, identities: AccountIdentityReader) -> None:
        """Initialize with authenticated identity reader."""
        self._identities = identities

    async def execute(self, request: InputData) -> OutputData:
        """Verify token and return trusted caller identity."""
        identity = await self._identities.read(request.token)
        return self.OutputData(subject=identity.subject, role=identity.role)
