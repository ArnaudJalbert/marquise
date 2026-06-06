"""Application DTOs for cinema use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class CreateCinemaRequest:
    """Request DTO for creating a new cinema."""

    name: str
    address: Optional[str] = None
    city: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be empty")


@dataclass(frozen=True, slots=True)
class CreateCinemaResponse:
    """Response DTO for cinema creation."""

    id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
