"""Domain exception re-exports."""

from marquise.domain.exceptions.base import DomainError
from marquise.domain.exceptions.cinema import (
    CinemaAlreadyExistsError,
    CinemaError,
    CinemaNotFoundError,
)
from marquise.domain.exceptions.movie import MovieError, MovieNotFoundError
from marquise.domain.exceptions.screening import ScreeningError, ScreeningNotFoundError

__all__ = [
    "CinemaAlreadyExistsError",
    "CinemaError",
    "CinemaNotFoundError",
    "DomainError",
    "MovieError",
    "MovieNotFoundError",
    "ScreeningError",
    "ScreeningNotFoundError",
]
