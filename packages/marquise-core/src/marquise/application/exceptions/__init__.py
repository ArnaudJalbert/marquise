"""Application exception re-exports."""

from marquise.application.exceptions.auth import (
    AuthAdministrationError,
    AuthenticationError,
    AuthorizationError,
    AuthUserNotFoundError,
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
    "ApplicationError",
    "AuthAdministrationError",
    "AuthenticationError",
    "AuthorizationError",
    "AuthUserNotFoundError",
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
