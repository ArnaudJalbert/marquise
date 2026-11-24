"""Tests for the calculate_page_offset helper."""

from __future__ import annotations

import pytest

from marquise.application.page import calculate_page_offset


@pytest.mark.parametrize(
    ("page", "size", "expected"),
    [
        (1, 10, 0),
        (3, 10, 20),
        (2, 1, 1),
    ],
)
def test_calculate_page_offset_skips_the_previous_pages(
    page: int, size: int, expected: int
) -> None:
    """A page starts after (page - 1) * size items."""
    assert calculate_page_offset(page, size) == expected
