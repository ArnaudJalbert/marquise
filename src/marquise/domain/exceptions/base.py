"""Base domain exception."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-layer exceptions.

    All custom exceptions raised by domain entities, value objects,
    and domain services should inherit from this class.
    """

    pass
