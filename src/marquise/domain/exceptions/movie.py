"""Movie-related domain exceptions."""

from __future__ import annotations

from marquise.domain.exceptions.base import DomainError


class MovieError(DomainError):
    """Base exception for movie-related errors."""

    pass


class MovieNotFoundError(MovieError):
    """Raised when a requested movie does not exist in the system."""

    pass
