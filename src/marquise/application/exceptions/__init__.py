"""Application exception re-exports."""

from marquise.application.exceptions.base import ApplicationError
from marquise.application.exceptions.cinema import (
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
)
from marquise.application.exceptions.source import (
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    SourceAlreadyExistsError,
    SourceNotFoundError,
)

__all__ = [
    "ApplicationError",
    "CinemaAlreadyExistsError",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "SourceAlreadyExistsError",
    "SourceNotFoundError",
]
