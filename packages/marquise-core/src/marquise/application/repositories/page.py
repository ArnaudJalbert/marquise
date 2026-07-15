"""Generic paginated result carrier for repository list queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page[T]:
    """A page of domain entities plus the total count matching the query.

    Attributes:
        items: The entities on this page (already limit/offset-applied, or
            the full result set if no limit was requested).
        total: Total number of entities matching the query, ignoring
            limit/offset.
    """

    items: list[T]
    total: int
