"""Tests for the get_page_offset helper."""

from __future__ import annotations

import pytest

from marquise.application.repositories.page import get_page_offset


@pytest.mark.parametrize(
    ("page", "size", "expected"),
    [
        (1, 10, 0),
        (3, 10, 20),
        (2, 1, 1),
    ],
)
def test_get_page_offset_skips_the_previous_pages(
    page: int, size: int, expected: int
) -> None:
    """A page starts after (page - 1) * size items."""
    assert get_page_offset(page, size) == expected
