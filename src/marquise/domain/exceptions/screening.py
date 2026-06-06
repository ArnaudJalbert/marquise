"""Screening-related domain exceptions."""

from __future__ import annotations

from marquise.domain.exceptions.base import DomainError


class ScreeningError(DomainError):
    """Base exception for screening-related errors."""

    pass


class ScreeningNotFoundError(ScreeningError):
    """Raised when a requested screening does not exist in the system."""

    pass
