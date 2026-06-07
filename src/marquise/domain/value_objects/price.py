"""Price value object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Price:
    """An immutable monetary value for a screening ticket.

    Attributes:
        value: The price as a float.
    """

    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Price cannot be negative")

    @classmethod
    def from_float(cls, amount: float) -> Price:
        """Create a Price from a float with validation.

        Args:
            amount: The ticket price.

        Returns:
            A new Price instance.

        Raises:
            ValueError: If the amount is negative.
        """
        if amount < 0:
            raise ValueError("Price cannot be negative")
        return cls(value=amount)

    def __str__(self) -> str:
        return f"{self.value:.2f}"
