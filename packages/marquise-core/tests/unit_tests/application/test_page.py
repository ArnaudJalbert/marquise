"""Tests for the page_window helper."""

from __future__ import annotations

import pytest

from marquise.application.page import page_window


@pytest.mark.parametrize(
    ("page", "size", "expected"),
    [
        (1, 10, 0),
        (3, 10, 20),
        (2, 1, 1),
    ],
)
def test_page_window_skips_the_previous_pages(
    page: int, size: int, expected: int
) -> None:
    """A page starts after (page - 1) * size items."""
    assert page_window(page, size) == expected
