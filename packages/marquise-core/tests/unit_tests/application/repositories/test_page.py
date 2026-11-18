"""Tests for the page_window helper."""

from __future__ import annotations

import pytest

from marquise.application.repositories.page import page_window


@pytest.mark.parametrize(
    ("page", "size", "expected"),
    [
        (1, 10, (10, 0)),
        (3, 10, (10, 20)),
        (2, 1, (1, 1)),
    ],
)
def test_page_window_turns_page_and_size_into_limit_and_offset(
    page: int, size: int, expected: tuple[int, int]
) -> None:
    """A sized page maps to a limit of size and an offset of (page - 1) * size."""
    assert page_window(page, size) == expected
