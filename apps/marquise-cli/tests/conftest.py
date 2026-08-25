"""Shared fixtures and helpers for marquise-cli tests."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import pytest

from marquise import ListCinemasUseCase, MarquiseFactory


@pytest.fixture
def mock_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory."""
    factory = create_autospec(MarquiseFactory, instance=True)
    factory.__aenter__.return_value = factory
    factory.__aexit__.return_value = False
    return factory


def make_cinema_data(
    cinema_id: str = "cin-001",
    name: str = "Test Cinema",
    address: str | None = "123 Test St",
    city: str | None = "Montreal",
    website: str | None = "https://example.com",
) -> ListCinemasUseCase.CinemaData:
    """Build a CinemaData instance for test setup."""
    return ListCinemasUseCase.CinemaData(
        id=cinema_id,
        name=name,
        address=address,
        city=city,
        website=website,
    )
