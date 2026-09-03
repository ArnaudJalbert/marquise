"""Application exception re-exports."""

from marquise.application.exceptions.auth import (
    AccountNotFoundError,
    AuthAdministrationError,
    AuthenticationError,
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
    "AccountNotFoundError",
    "ApplicationError",
    "AuthAdministrationError",
    "AuthenticationError",
    "AuthorizationError",
    "CinemaAlreadyExistsError",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "MovieNotFoundError",
    "ScreeningAlreadyExistsError",
    "ScreeningNotFoundError",
    "ScreeningUpdateNotFoundError",
    "SelfDemotionError",
    "SourceAlreadyExistsError",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
]
