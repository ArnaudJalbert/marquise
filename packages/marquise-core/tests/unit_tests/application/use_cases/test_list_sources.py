"""Tests for ListSourcesUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import SourceDefinitionRepository
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.domain.entities import SourceDefinition
from marquise.domain.value_objects import SourceName


@pytest.mark.asyncio
async def test_list_sources_returns_all() -> None:
    """Verify list returns all registered sources."""
    mock_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_repo.find_all.return_value = [
        SourceDefinition(
            name=SourceName(value="cineplex"),
            display_name="Cineplex",
            description="Cineplex cinemas",
        ),
        SourceDefinition(
            name=SourceName(value="cinema_du_parc"),
            display_name="Cinema du Parc",
            description=None,
        ),
    ]

    use_case = ListSourcesUseCase(source_repository=mock_repo)
    request = ListSourcesUseCase.InputData()

    response = await use_case.execute(request)

    assert len(response.sources) == 2
    assert response.sources[0].name == "cineplex"
    assert response.sources[0].display_name == "Cineplex"
    assert response.sources[1].name == "cinema_du_parc"
    mock_repo.find_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_sources_returns_empty_list() -> None:
    """Verify list returns empty list when no sources exist."""
    mock_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_repo.find_all.return_value = []

    use_case = ListSourcesUseCase(source_repository=mock_repo)
    request = ListSourcesUseCase.InputData()

    response = await use_case.execute(request)
    assert response.sources == []
