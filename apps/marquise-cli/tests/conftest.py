"""Shared fixtures and helpers for marquise-cli tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from marquise import (
    CinemaUseCases,
    CreateSourceUseCase,
    DeleteCinemaUseCase,
    DeleteSourceUseCase,
    GetCinemaSourceUseCase,
    ListCinemasUseCase,
    MarquiseFactory,
    MovieUseCases,
    ScreeningUseCases,
    SourceUseCases,
    UpdateCinemaUseCase,
)
from marquise_cli import helpers

UseCaseType = type[
    CreateSourceUseCase
    | DeleteCinemaUseCase
    | DeleteSourceUseCase
    | ListCinemasUseCase
    | UpdateCinemaUseCase
]


def stub_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory with an autospecced container per area."""
    factory = create_autospec(MarquiseFactory, instance=True)
    factory.cinemas = create_autospec(CinemaUseCases, instance=True)
    factory.movies = create_autospec(MovieUseCases, instance=True)
    factory.screenings = create_autospec(ScreeningUseCases, instance=True)
    factory.sources = create_autospec(SourceUseCases, instance=True)
    return factory


@pytest.fixture
def mock_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory."""
    return stub_factory()


@dataclass
class FactorySession:
    """Stand in for create_factory_session and record whether it closed."""

    factory: MagicMock
    closed: bool = False

    @asynccontextmanager
    async def open(self) -> AsyncIterator[MagicMock]:
        """Yield the stub factory, then record that the session closed."""
        try:
            yield self.factory
        finally:
            self.closed = True


def patch_factory_session(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> FactorySession:
    """Make every CLI command open a session over the given stub factory."""
    session = FactorySession(factory)
    monkeypatch.setattr(helpers, "create_factory_session", session.open)
    return session


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


@dataclass(frozen=True)
class Command:
    """A selected CLI command and its failing application dependency."""

    argv: tuple[str, ...]
    session: FactorySession
    use_case: MagicMock


@pytest.fixture
def command(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Command:
    """Supply interactive selections and a factory without external services."""
    argv, module, attribute, use_case_type, selections = request.param
    factory = _stub_factory_with_cineplex_source()
    use_case = create_autospec(use_case_type, instance=True)
    use_case.InputData = use_case_type.InputData
    area, use_case_name = attribute.split(".")
    setattr(getattr(factory, area), use_case_name, use_case)
    session = patch_factory_session(monkeypatch, factory)
    _stub_selections(module, selections, monkeypatch)
    return Command(argv, session, use_case)


def _stub_factory_with_cineplex_source() -> MagicMock:
    """Provide a factory whose source lookup resolves to Cineplex."""
    factory = stub_factory()
    source = create_autospec(GetCinemaSourceUseCase, instance=True)
    source.InputData = GetCinemaSourceUseCase.InputData
    source.execute.return_value = GetCinemaSourceUseCase.OutputData(
        "cin-001", "cineplex", "Cineplex"
    )
    factory.sources.get_cinema_source_use_case = source
    return factory


def _stub_selections(
    module: ModuleType,
    selections: dict[str, ListCinemasUseCase.CinemaData | str | tuple[date, date]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace interactive selection prompts with fixed answers."""
    for attribute, selection in selections.items():
        monkeypatch.setattr(module, attribute, AsyncMock(return_value=selection))
