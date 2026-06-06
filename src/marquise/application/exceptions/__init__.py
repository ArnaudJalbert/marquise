"""Application-layer exceptions for Marquise."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for all application-layer exceptions."""

    pass


class CinemaIdAlreadyExistsError(ApplicationError):
    """Raised when a generated cinema ID already exists in the repository."""

    pass
