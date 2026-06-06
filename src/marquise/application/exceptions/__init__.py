"""Application exception re-exports."""

from marquise.application.exceptions.base import ApplicationError
from marquise.application.exceptions.cinema import (
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
)

__all__ = [
    "ApplicationError",
    "CinemaAlreadyExistsError",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
]
