"""Shared fixtures and helpers for marquise-cli tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from marquise import (
    CreateSourceUseCase,
    DeleteCinemaUseCase,
    DeleteSourceUseCase,
    ListCinemasUseCase,
    MarquiseFactory,
    UpdateCinemaUseCase,
)

UseCaseType = type[
    CreateSourceUseCase
    | DeleteCinemaUseCase
    | DeleteSourceUseCase
    | ListCinemasUseCase
    | UpdateCinemaUseCase
]


@pytest.fixture
def mock_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory."""
    factory = create_autospec(MarquiseFactory, instance=True)
    factory.__aenter__.return_value = factory
    factory.__aexit__.return_value = False
    return factory


def mock_use_case(use_case_type: UseCaseType) -> MagicMock:
    """Provide a mocked use case with its real input DTO constructor."""
    use_case = create_autospec(use_case_type, instance=True)
    use_case.execute = AsyncMock()
    use_case.InputData = use_case_type.InputData
    return use_case


@pytest.fixture
def mock_list_cinemas_use_case() -> MagicMock:
    """Provide a mocked ListCinemasUseCase."""
    return mock_use_case(ListCinemasUseCase)


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
