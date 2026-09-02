"""Authentication and account-administration errors."""

from marquise.application.exceptions.base import ApplicationError


class AuthenticationError(ApplicationError):
    """Credentials cannot identify a Marquise caller."""


class AuthorizationError(ApplicationError):
    """Authenticated caller lacks required authorization."""


class AuthAdministrationError(ApplicationError):
    """Supabase account administration failed."""


class AuthUserNotFoundError(AuthAdministrationError):
    """Requested Supabase Auth user does not exist."""


class SelfDemotionError(AuthAdministrationError):
    """Administrator attempted to remove their own Administrator role."""
