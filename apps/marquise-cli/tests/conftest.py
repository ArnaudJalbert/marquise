"""Shared fixtures and helpers for marquise-cli tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from marquise import ListCinemasUseCase


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for MarquiseFactory creation."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


@pytest.fixture
def mock_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory."""
    factory = MagicMock()
    factory.__aenter__ = AsyncMock(return_value=factory)
    factory.__aexit__ = AsyncMock(return_value=False)
    factory.initialize = AsyncMock()
    factory.shutdown = AsyncMock()
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
