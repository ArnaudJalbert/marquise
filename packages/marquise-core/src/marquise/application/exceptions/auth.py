"""Authentication and account-administration errors."""

from marquise.application.exceptions.base import ApplicationError


class AuthenticationError(ApplicationError):
    """Credentials cannot identify a Marquise caller."""


class AuthenticationServiceUnavailableError(ApplicationError):
    """The external identity service cannot currently verify callers."""


class AuthorizationError(ApplicationError):
    """Authenticated caller lacks required authorization."""


class AuthAdministrationError(ApplicationError):
    """Supabase account administration failed."""


class AccountAlreadyExistsError(AuthAdministrationError):
    """Requested account already exists."""


class AccountNotFoundError(AuthAdministrationError):
    """Requested Supabase Auth account does not exist."""


class SelfDemotionError(AuthAdministrationError):
    """Administrator attempted to remove their own Administrator role."""
