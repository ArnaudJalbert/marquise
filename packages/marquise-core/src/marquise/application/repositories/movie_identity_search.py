"""Search for a movie identity without choosing its metadata provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MovieIdentityCandidate:
    """A possible film identity, with its provider named explicitly."""

    provider: str
    id: str
    title: str
    release_year: int | None


class MovieIdentitySearch(ABC):
    """Find possible movie identities by title and optional release year."""

    @abstractmethod
    async def search(
        self, title: str, year: int | None
    ) -> list[MovieIdentityCandidate]:
        """Return candidates from the configured provider."""
        ...
