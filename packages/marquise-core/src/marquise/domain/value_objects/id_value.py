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

    def __post_init__(self) -> None:
        """Validate that value is not empty or whitespace-only.

        Raises:
            ValueError: If value is empty or whitespace-only.
        """
        if not self.value.strip():
            raise ValueError("value must not be empty or whitespace-only")

    def __str__(self) -> str:
        return self.value
