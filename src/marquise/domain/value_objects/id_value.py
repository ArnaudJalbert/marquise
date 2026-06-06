"""ID value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IdValue:
    """An immutable string identifier for domain entities.

    Attributes:
        value: The unique string identifier.
    """

    value: str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)
