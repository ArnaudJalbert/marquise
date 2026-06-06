"""Cinema-related domain exceptions."""

from __future__ import annotations

from marquise.domain.exceptions.base import DomainError


class CinemaError(DomainError):
    """Base exception for cinema-related errors."""

    pass


class CinemaNotFoundError(CinemaError):
    """Raised when a requested cinema does not exist in the system."""

    pass


class CinemaAlreadyExistsError(CinemaError):
    """Raised when attempting to create a cinema that already exists."""

    pass
