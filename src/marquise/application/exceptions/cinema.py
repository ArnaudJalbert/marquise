"""Cinema-related application exceptions."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


class CinemaIdAlreadyExistsError(ApplicationError):
    """Raised when a generated cinema ID already exists in the repository.

    This indicates an extremely rare UUID collision and should be handled
    by regenerating the ID and retrying.
    """

    pass
