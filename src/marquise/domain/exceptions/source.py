"""Source-related domain exceptions."""

from __future__ import annotations

from marquise.domain.exceptions.base import DomainError


class SourceError(DomainError):
    """Base exception for source-related errors."""

    pass


class SourceNotFoundError(SourceError):
    """Raised when a requested source does not exist in the system."""

    pass


class SourceAlreadyExistsError(SourceError):
    """Raised when attempting to create a source that already exists."""

    pass


class CinemaSourceAssignmentNotFoundError(SourceError):
    """Raised when no assignment exists for a given cinema."""

    pass


class CinemaSourceAssignmentAlreadyExistsError(SourceError):
    """Raised when attempting to assign a source to a cinema that already has one."""

    pass
