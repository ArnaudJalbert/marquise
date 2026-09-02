"""Read port for verified caller identity data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class UserIdentityReader(ABC):
    """Verify an access token and return only authorization data."""

    @dataclass(frozen=True, slots=True)
    class IdentityData:
        """Minimal trusted identity projection."""

        subject: str
        role: str

    @abstractmethod
    async def read(self, token: str) -> IdentityData:
        """Verify token and return minimal caller identity."""
        ...
