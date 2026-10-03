"""Application exception re-exports."""

from marquise.application.exceptions.auth import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    AuthAdministrationError,
    AuthenticationError,
    AuthenticationServiceUnavailableError,
    AuthorizationError,
    SelfDemotionError,
)
from marquise.application.exceptions.base import ApplicationError
from marquise.application.exceptions.cinema import (
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
)
from marquise.application.exceptions.movie import (
    MovieNotFoundError,
    TooManyMovieIdsError,
)
from marquise.application.exceptions.screening import (
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
    ScreeningNotFoundError,
    ScreeningUpdateNotFoundError,
)
from marquise.application.exceptions.source import (
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    SourceAlreadyExistsError,
    SourceNotFoundError,
)

__all__ = [
    "AccountAlreadyExistsError",
    "AccountNotFoundError",
    "ApplicationError",
    "AuthAdministrationError",
    "AuthenticationError",
    "AuthenticationServiceUnavailableError",
    "AuthorizationError",
    "CinemaAlreadyExistsError",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "MovieNotFoundError",
    "ScreeningAlreadyExistsError",
    "ScreeningExternalIdConflictError",
    "ScreeningNotFoundError",
    "ScreeningUpdateNotFoundError",
    "SelfDemotionError",
    "SourceAlreadyExistsError",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
]
