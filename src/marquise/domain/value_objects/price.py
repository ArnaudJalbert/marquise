"""Price value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Price:
    """Price of a screening."""

    value: float

    @classmethod
    def from_float(cls, amount: float) -> Price:
        """Create a Price from a float."""
        if amount < 0:
            raise ValueError("Price cannot be negative")
        return cls(value=amount)

    def __str__(self) -> str:
        return f"{self.value:.2f}"

    def __hash__(self) -> int:
        return hash(self.value)
