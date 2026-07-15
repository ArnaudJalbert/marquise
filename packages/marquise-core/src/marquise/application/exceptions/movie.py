"""Movie-related application exceptions."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


class MovieNotFoundError(ApplicationError):
    """Raised when a requested movie does not exist in the repository."""

    pass
