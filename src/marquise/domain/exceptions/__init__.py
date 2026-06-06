"""Domain exceptions for Marquise."""

from __future__ import annotations


class DomainException(Exception):
    """Base class for all domain exceptions."""

    pass


class MovieError(DomainException):
    """Exception related to movies."""

    pass


class CinemaError(DomainException):
    """Exception related to cinemas."""

    pass


class ScreeningError(DomainException):
    """Exception related to screenings."""

    pass


class MovieNotFoundError(MovieError):
    """Raised when a movie is not found."""

    pass


class CinemaNotFoundError(CinemaError):
    """Raised when a cinema is not found."""

    pass


class CinemaAlreadyExistsError(CinemaError):
    """Raised when a cinema with the same name and address already exists."""

    pass


class ScreeningNotFoundError(ScreeningError):
    """Raised when a screening is not found."""

    pass
