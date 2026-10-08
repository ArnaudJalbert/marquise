"""Authorize an Administrator and provision an identified Editor Bot."""

import re
from dataclasses import dataclass, field

from marquise.application.exceptions.auth import (
    AccountAlreadyExistsError,
    AuthAdministrationError,
)
from marquise.application.repositories.bot_repository import BotRepository
from marquise.application.use_cases.auth._validation import normalize_email
from marquise.application.use_cases.auth.authenticate_administrator import (
    AuthenticateAdministratorUseCase,
)


class CreateBotUseCase:
    """Create a Bot and return its refresh token once."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Administrator credentials and the chosen Bot Identifier."""

        administrator_email: str
        administrator_password: str = field(repr=False)
        bot_id: str

        def __post_init__(self) -> None:
            """Validate credentials and the lowercase Bot Identifier."""
            normalize_email(self.administrator_email)
            if not self.administrator_password:
                raise ValueError("administrator_password must not be empty")
            if not re.fullmatch(r"[a-z0-9._-]+", self.bot_id):
                raise ValueError(
                    "Bot Identifier must contain only lowercase letters, "
                    "numbers, -, _, and ."
                )

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Provisioned Bot identity and transient credentials."""

        account_id: str
        bot_id: str
        refresh_token: str = field(repr=False)

    def __init__(
        self,
        bots: BotRepository,
        authenticate_administrator: AuthenticateAdministratorUseCase,
    ) -> None:
        """Inject Bot storage and the shared Administrator authorization gate."""
        self._bots = bots
        self._authenticate_administrator = authenticate_administrator

    async def execute(self, request: InputData) -> OutputData:
        """Authorize, reject duplicates, and provision an Editor Bot."""
        await self._authenticate_administrator.execute(
            self._authenticate_administrator.InputData(
                email=normalize_email(request.administrator_email),
                password=request.administrator_password,
            )
        )
        if await self._bots.identifier_exists(request.bot_id):
            raise AccountAlreadyExistsError("Bot Identifier is already assigned")
        session = await self._bots.create_anonymous()
        try:
            await self._bots.assign_editor(session.account_id, request.bot_id)
        except AuthAdministrationError as setup_error:
            try:
                await self._bots.delete(session.account_id)
            except AuthAdministrationError as cleanup_error:
                raise AuthAdministrationError(
                    "Bot setup failed and cleanup failed for account "
                    f"{session.account_id}. "
                    "Delete this account through Supabase administration."
                ) from cleanup_error
            raise setup_error
        return self.OutputData(
            session.account_id, request.bot_id, session.refresh_token
        )
