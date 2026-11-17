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


def page_window(page: int, size: int | None) -> tuple[int | None, int]:
    """Turn a 1-based page number and page size into a limit and offset.

    Args:
        page: The 1-based page number.
        size: The page size, or ``None`` for no pagination.

    Returns:
        A ``(limit, offset)`` pair. With ``size=None`` the limit is ``None``
        and the offset is 0.
    """
    if size is None:
        return None, 0
    return size, (page - 1) * size
