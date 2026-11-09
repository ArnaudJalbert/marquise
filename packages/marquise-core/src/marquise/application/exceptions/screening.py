"""Screening-related application exceptions."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


class ScreeningAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a duplicate screening."""

    pass


class ScreeningExternalIdConflictError(ApplicationError):
    """Raised when an external ID belongs to a different screening."""


class ScreeningIdempotencyConflictError(ApplicationError):
    """A successful key was reused for a different intended request."""


class ScreeningNotFoundError(ApplicationError):
    """Raised when a requested screening does not exist in the repository."""

    pass


class ScreeningUpdateNotFoundError(ApplicationError):
    """Raised when an existing screening disappears before it can be updated."""

    pass


class ScreeningWriteConflictError(ApplicationError):
    """The checked persistence state changed; no write was committed."""


class ScreeningImportRetryExhaustedError(ApplicationError):
    """An import could not commit after bounded fresh-state attempts."""


class ScreeningWriteBusyError(ApplicationError):
    """A duplicate could not obtain its committed result within the wait limit."""


class TooManyScreeningDaysError(ApplicationError):
    """Raised when a daily screening count spans more days than allowed."""
