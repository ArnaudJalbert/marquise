"""TMDB movie identity search contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TmdbCandidate:
    """A possible film identity from TMDB."""

    id: str
    title: str
    release_year: int | None


class TmdbSearch(ABC):
    """Find TMDB films by a source title and optional release year."""

    @abstractmethod
    async def search(self, title: str, year: int | None) -> list[TmdbCandidate]:
        """Return all candidate identities; an empty list means no matches."""
        ...
