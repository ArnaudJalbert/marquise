"""Tests for SourceController."""

from __future__ import annotations

from datetime import date
from unittest.mock import create_autospec

import pytest

from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import (
    CreateScreeningsCommand,
)
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.infrastructure.controllers.source_controller import SourceController


@pytest.fixture
def mock_create_use_case() -> CreateSourceUseCase:
    """Provide a mocked CreateSourceUseCase."""
    return create_autospec(CreateSourceUseCase, instance=True)


@pytest.fixture
def mock_list_use_case() -> ListSourcesUseCase:
    """Provide a mocked ListSourcesUseCase."""
    return create_autospec(ListSourcesUseCase, instance=True)


@pytest.fixture
def mock_delete_use_case() -> DeleteSourceUseCase:
    """Provide a mocked DeleteSourceUseCase."""
    return create_autospec(DeleteSourceUseCase, instance=True)


@pytest.fixture
def mock_assign_use_case() -> AssignSourceUseCase:
    """Provide a mocked AssignSourceUseCase."""
    return create_autospec(AssignSourceUseCase, instance=True)


@pytest.fixture
def mock_unassign_use_case() -> UnassignSourceUseCase:
    """Provide a mocked UnassignSourceUseCase."""
    return create_autospec(UnassignSourceUseCase, instance=True)


@pytest.fixture
def mock_get_use_case() -> GetCinemaSourceUseCase:
    """Provide a mocked GetCinemaSourceUseCase."""
    return create_autospec(GetCinemaSourceUseCase, instance=True)


@pytest.fixture
def mock_list_registry_use_case() -> ListRegistrySourcesUseCase:
    """Provide a mocked ListRegistrySourcesUseCase."""
    return create_autospec(ListRegistrySourcesUseCase, instance=True)


@pytest.fixture
def mock_fetch_screenings_use_case() -> FetchScreeningsFromSourceQuery:
    """Provide a mocked FetchScreeningsFromSourceQuery."""
    return create_autospec(FetchScreeningsFromSourceQuery, instance=True)


@pytest.fixture
def mock_create_movies_use_case() -> CreateMissingMoviesCommand:
    """Provide a mocked CreateMissingMoviesCommand."""
    return create_autospec(CreateMissingMoviesCommand, instance=True)


@pytest.fixture
def mock_create_screenings_use_case() -> CreateScreeningsCommand:
    """Provide a mocked CreateScreeningsCommand."""
    return create_autospec(CreateScreeningsCommand, instance=True)


@pytest.fixture
def controller(
    mock_create_use_case: CreateSourceUseCase,
    mock_list_use_case: ListSourcesUseCase,
    mock_delete_use_case: DeleteSourceUseCase,
    mock_assign_use_case: AssignSourceUseCase,
    mock_unassign_use_case: UnassignSourceUseCase,
    mock_get_use_case: GetCinemaSourceUseCase,
    mock_list_registry_use_case: ListRegistrySourcesUseCase,
    mock_fetch_screenings_use_case: FetchScreeningsFromSourceQuery,
    mock_create_movies_use_case: CreateMissingMoviesCommand,
    mock_create_screenings_use_case: CreateScreeningsCommand,
) -> SourceController:
    """Provide a SourceController wired to mocks."""
    return SourceController(
        create_source_use_case=mock_create_use_case,
        list_sources_use_case=mock_list_use_case,
        delete_source_use_case=mock_delete_use_case,
        assign_source_use_case=mock_assign_use_case,
        unassign_source_use_case=mock_unassign_use_case,
        get_cinema_source_use_case=mock_get_use_case,
        list_registry_sources_use_case=mock_list_registry_use_case,
        fetch_screenings_use_case=mock_fetch_screenings_use_case,
        create_movies_use_case=mock_create_movies_use_case,
        create_screenings_use_case=mock_create_screenings_use_case,
    )


# ── create_source ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_source_delegates(
    controller: SourceController,
    mock_create_use_case: CreateSourceUseCase,
) -> None:
    """Verify create_source delegates to the use case."""
    expected = CreateSourceUseCase.OutputData(
        name="cineplex",
        display_name="Cineplex",
        description="Cineplex cinemas",
    )
    mock_create_use_case.execute.return_value = expected

    result = await controller.create_source(
        name="cineplex",
        display_name="Cineplex",
        description="Cineplex cinemas",
    )

    assert result == expected
    mock_create_use_case.execute.assert_awaited_once()
    input_data = mock_create_use_case.execute.call_args[0][0]
    assert isinstance(input_data, CreateSourceUseCase.InputData)
    assert input_data.name == "cineplex"


# ── list_sources ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sources_delegates(
    controller: SourceController,
    mock_list_use_case: ListSourcesUseCase,
) -> None:
    """Verify list_sources delegates to the use case."""
    source_data = ListSourcesUseCase.SourceData(name="s", display_name="S")
    expected = ListSourcesUseCase.OutputData(sources=[source_data])
    mock_list_use_case.execute.return_value = expected

    result = await controller.list_sources()

    assert result == expected
    mock_list_use_case.execute.assert_awaited_once()


# ── delete_source ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_source_delegates(
    controller: SourceController,
    mock_delete_use_case: DeleteSourceUseCase,
) -> None:
    """Verify delete_source delegates to the use case."""
    expected = DeleteSourceUseCase.OutputData(source_name="cineplex")
    mock_delete_use_case.execute.return_value = expected

    result = await controller.delete_source(source_name="cineplex")

    assert result == expected
    mock_delete_use_case.execute.assert_awaited_once()
    input_data = mock_delete_use_case.execute.call_args[0][0]
    assert isinstance(input_data, DeleteSourceUseCase.InputData)
    assert input_data.source_name == "cineplex"


# ── assign_source ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_source_delegates(
    controller: SourceController,
    mock_assign_use_case: AssignSourceUseCase,
) -> None:
    """Verify assign_source delegates to the use case."""
    expected = AssignSourceUseCase.OutputData(
        cinema_id="cin-001", source_name="cineplex"
    )
    mock_assign_use_case.execute.return_value = expected

    result = await controller.assign_source(cinema_id="cin-001", source_name="cineplex")

    assert result == expected
    mock_assign_use_case.execute.assert_awaited_once()
    input_data = mock_assign_use_case.execute.call_args[0][0]
    assert isinstance(input_data, AssignSourceUseCase.InputData)
    assert input_data.cinema_id == "cin-001"
    assert input_data.source_name == "cineplex"


# ── unassign_source ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unassign_source_delegates(
    controller: SourceController,
    mock_unassign_use_case: UnassignSourceUseCase,
) -> None:
    """Verify unassign_source delegates to the use case."""
    expected = UnassignSourceUseCase.OutputData(cinema_id="cin-001")
    mock_unassign_use_case.execute.return_value = expected

    result = await controller.unassign_source(cinema_id="cin-001")

    assert result == expected
    mock_unassign_use_case.execute.assert_awaited_once()
    input_data = mock_unassign_use_case.execute.call_args[0][0]
    assert isinstance(input_data, UnassignSourceUseCase.InputData)
    assert input_data.cinema_id == "cin-001"


# ── get_cinema_source ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_cinema_source_delegates(
    controller: SourceController,
    mock_get_use_case: GetCinemaSourceUseCase,
) -> None:
    """Verify get_cinema_source delegates to the use case."""
    expected = GetCinemaSourceUseCase.OutputData(
        cinema_id="cin-001",
        source_name="cineplex",
        source_display_name="Cineplex",
    )
    mock_get_use_case.execute.return_value = expected

    result = await controller.get_cinema_source(cinema_id="cin-001")

    assert result == expected
    mock_get_use_case.execute.assert_awaited_once()
    input_data = mock_get_use_case.execute.call_args[0][0]
    assert isinstance(input_data, GetCinemaSourceUseCase.InputData)
    assert input_data.cinema_id == "cin-001"


# ── list_registry_sources ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_registry_sources_delegates(
    controller: SourceController,
    mock_list_registry_use_case: ListRegistrySourcesUseCase,
) -> None:
    """Verify list_registry_sources delegates to the use case."""
    source_entry = ListRegistrySourcesUseCase.SourceEntry(
        name="cinemacinema",
    )
    expected = ListRegistrySourcesUseCase.OutputData(sources=[source_entry])
    mock_list_registry_use_case.execute.return_value = expected

    result = await controller.list_registry_sources()

    assert result == expected
    mock_list_registry_use_case.execute.assert_awaited_once()
    input_data = mock_list_registry_use_case.execute.call_args[0][0]
    assert isinstance(input_data, ListRegistrySourcesUseCase.InputData)


# ── import_screenings ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_screenings_sequences_the_three_use_cases(
    controller: SourceController,
    mock_fetch_screenings_use_case: FetchScreeningsFromSourceQuery,
    mock_create_movies_use_case: CreateMissingMoviesCommand,
    mock_create_screenings_use_case: CreateScreeningsCommand,
) -> None:
    """Verify import_screenings runs the fetch → movies → screenings chain."""
    mock_fetch_screenings_use_case.execute.return_value = (
        FetchScreeningsFromSourceQuery.OutputData(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            movies=(),
            screenings=(),
        )
    )
    mock_create_movies_use_case.execute.return_value = (
        CreateMissingMoviesCommand.OutputData(movies=())
    )
    mock_create_screenings_use_case.execute.return_value = (
        CreateScreeningsCommand.OutputData(
            screenings=(),
            total_count=3,
            imported_count=2,
            updated_count=1,
            skipped_count=0,
        )
    )

    result = await controller.import_screenings(
        cinema_id="cin-123",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 8),
    )

    assert result.cinema_id == "cin-123"
    assert result.cinema_name == "Cinéma Beaubien"
    assert result.source_name == "cinemacinema"
    assert result.total_count == 3
    assert result.imported_count == 2
    assert result.updated_count == 1
    assert result.skipped_count == 0

    fetch_input = mock_fetch_screenings_use_case.execute.call_args[0][0]
    assert isinstance(fetch_input, FetchScreeningsFromSourceQuery.InputData)
    assert fetch_input.cinema_id == "cin-123"

    movies_input = mock_create_movies_use_case.execute.call_args[0][0]
    assert isinstance(movies_input, CreateMissingMoviesCommand.InputData)

    screenings_input = mock_create_screenings_use_case.execute.call_args[0][0]
    assert isinstance(screenings_input, CreateScreeningsCommand.InputData)
