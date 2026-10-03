"""Screening-related application exceptions."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


class ScreeningAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a duplicate screening."""

    pass


class ScreeningExternalIdConflictError(ApplicationError):
    """Raised when an external ID belongs to a different screening."""


class ScreeningNotFoundError(ApplicationError):
    """Raised when a requested screening does not exist in the repository."""

    pass


class ScreeningUpdateNotFoundError(ApplicationError):
    """Raised when an existing screening disappears before it can be updated."""

    pass
