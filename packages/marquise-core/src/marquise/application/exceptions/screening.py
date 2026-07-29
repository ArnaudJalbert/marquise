"""Screening-related application exceptions."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


class ScreeningAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a duplicate screening."""

    pass


class ScreeningNotFoundError(ApplicationError):
    """Raised when a requested screening does not exist in the repository."""

    pass


class ScreeningUpdateNotFoundError(ApplicationError):
    """Raised when an existing screening cannot be updated because its underlying
    row was deleted concurrently or the conflict was on a different constraint
    (e.g. external_id belongs to a different screening)."""

    pass
