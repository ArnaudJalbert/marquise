"""Authenticate a CLI Administrator."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions.auth import AuthorizationError
from marquise.application.readers.account_identity_reader import (
    AccountIdentityReader,
)
from marquise.application.repositories.password_authentication_repository import (
    PasswordAuthenticationRepository,
)
from marquise.application.use_cases.auth._validation import normalize_email
from marquise.domain.value_objects.marquise_role import MarquiseRole


class AuthenticateAdministratorUseCase:
    """Authenticate credentials and require Administrator authorization."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Administrator email and password."""

        email: str
        password: str

        def __post_init__(self) -> None:
            """Validate credentials without mutating delivery input."""
            normalize_email(self.email)
            if not self.password:
                raise ValueError("password must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Authenticated Administrator identity."""

        subject: str

    def __init__(
        self,
        passwords: PasswordAuthenticationRepository,
        identities: AccountIdentityReader,
    ) -> None:
        """Initialize with password and token repositories."""
        self._passwords = passwords
        self._identities = identities

    async def execute(self, request: InputData) -> OutputData:
        """Authenticate credentials and reject non-Administrators.

        Raises:
            AuthenticationError: If the credentials or issued token are invalid.
            AuthenticationServiceUnavailableError: If authentication is unavailable.
            AuthorizationError: If the authenticated account is not an Administrator.
        """
        token = await self._passwords.issue_access_token(
            normalize_email(request.email), request.password
        )
        identity = await self._identities.read(token)
        if identity.role != MarquiseRole.ADMINISTRATOR.value:
            raise AuthorizationError("Administrator role required")
        return self.OutputData(subject=identity.subject)
