"""Application exception re-exports."""

from marquise.application.exceptions.base import ApplicationError
from marquise.application.exceptions.cinema import CinemaIdAlreadyExistsError

__all__ = [
    "ApplicationError",
    "CinemaIdAlreadyExistsError",
]
