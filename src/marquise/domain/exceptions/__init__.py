"""Domain exception re-exports."""

from marquise.domain.exceptions.base import DomainError
from marquise.domain.exceptions.cinema import (
    CinemaAlreadyExistsError,
    CinemaError,
    CinemaNotFoundError,
)
from marquise.domain.exceptions.movie import MovieError, MovieNotFoundError
from marquise.domain.exceptions.screening import ScreeningError, ScreeningNotFoundError
from marquise.domain.exceptions.source import (
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    SourceAlreadyExistsError,
    SourceError,
    SourceNotFoundError,
)

__all__ = [
    "CinemaAlreadyExistsError",
    "CinemaError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "DomainError",
    "MovieError",
    "MovieNotFoundError",
    "ScreeningError",
    "ScreeningNotFoundError",
    "SourceAlreadyExistsError",
    "SourceError",
    "SourceNotFoundError",
]
