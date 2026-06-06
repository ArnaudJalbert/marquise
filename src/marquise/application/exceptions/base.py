"""Base application-layer exception."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for all application-layer exceptions.

    All custom exceptions raised by use cases should inherit from
    this class to distinguish them from domain or infrastructure errors.
    """

    pass
