"""Shared non-fixture helpers for marquise-cli tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, create_autospec

from marquise import (
    DeleteCinemaUseCase,
    ListCinemasUseCase,
    UpdateCinemaUseCase,
)

UseCaseType = type[DeleteCinemaUseCase | ListCinemasUseCase | UpdateCinemaUseCase]


def mock_use_case(use_case_type: UseCaseType) -> MagicMock:
    """Provide a mocked cinema use case with its real input DTO constructor."""
    use_case = create_autospec(use_case_type, instance=True)
    use_case.execute = AsyncMock()
    use_case.InputData = use_case_type.InputData
    return use_case


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
