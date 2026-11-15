"""Shared fixtures and helpers for marquise-cli tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from marquise import (
    DeleteCinemaUseCase,
    GetCinemaSourceUseCase,
    ListCinemasUseCase,
    MarquiseFactory,
    UpdateCinemaUseCase,
)

UseCaseType = type[DeleteCinemaUseCase | ListCinemasUseCase | UpdateCinemaUseCase]


@pytest.fixture
def mock_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory."""
    factory = create_autospec(MarquiseFactory, instance=True)
    factory.__aenter__.return_value = factory
    factory.__aexit__.return_value = False
    return factory


def mock_use_case(use_case_type: UseCaseType) -> MagicMock:
    """Provide a mocked cinema use case with its real input DTO constructor."""
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


@dataclass(frozen=True)
class Command:
    """A selected CLI command and its failing application dependency."""

    argv: tuple[str, ...]
    factory: MagicMock
    use_case: MagicMock


@pytest.fixture
def command(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Command:
    """Supply interactive selections and a factory without external services."""
    argv, module, attribute, use_case_type, selections = request.param
    factory = _stub_factory()
    use_case = create_autospec(use_case_type, instance=True)
    use_case.InputData = use_case_type.InputData
    setattr(factory, attribute, use_case)
    monkeypatch.setattr(module, "MarquiseFactory", lambda: factory)
    _stub_selections(module, selections, monkeypatch)
    return Command(argv, factory, use_case)


def _stub_factory() -> MagicMock:
    """Provide a factory whose source lookup resolves to Cineplex."""
    factory = create_autospec(MarquiseFactory, instance=True)
    source = create_autospec(GetCinemaSourceUseCase, instance=True)
    source.InputData = GetCinemaSourceUseCase.InputData
    source.execute.return_value = GetCinemaSourceUseCase.OutputData(
        "cin-001", "cineplex", "Cineplex"
    )
    factory.get_cinema_source_use_case = source
    return factory


def _stub_selections(
    module: ModuleType,
    selections: dict[str, ListCinemasUseCase.CinemaData | str | tuple[date, date]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace interactive selection prompts with fixed answers."""
    for attribute, selection in selections.items():
        monkeypatch.setattr(module, attribute, AsyncMock(return_value=selection))
