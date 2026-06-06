"""Cinema-related application exceptions."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


class CinemaAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a cinema with a duplicate name+address."""

    pass


class CinemaNotFoundError(ApplicationError):
    """Raised when a requested cinema does not exist in the repository."""

    pass


class CinemaIdAlreadyExistsError(ApplicationError):
    """Raised when a generated cinema ID already exists in the repository.

    This indicates an extremely rare UUID collision and should be handled
    by regenerating the ID and retrying.
    """

    pass
