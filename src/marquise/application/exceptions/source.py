"""Source-related application exceptions."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


class SourceAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a source that already exists."""

    pass


class SourceNotFoundError(ApplicationError):
    """Raised when a requested source does not exist in the repository."""

    pass


class CinemaSourceAssignmentAlreadyExistsError(ApplicationError):
    """Raised when attempting to assign a source to a cinema that already has one."""

    pass


class CinemaSourceAssignmentNotFoundError(ApplicationError):
    """Raised when no assignment exists for a given cinema."""

    pass
