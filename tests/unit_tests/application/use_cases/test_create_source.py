"""Tests for CreateSourceUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import SourceAlreadyExistsError
from marquise.application.repositories import SourceDefinitionRepository
from marquise.application.use_cases import CreateSourceUseCase
from marquise.domain.entities import SourceDefinition
from marquise.domain.value_objects import SourceName


@pytest.mark.asyncio
async def test_create_source_saves_and_returns_response() -> None:
    """Verify the happy path: source is saved and response data is correct."""
    mock_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_repo.find_by_name.return_value = None
    mock_repo.save.return_value = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
        description="Cineplex cinemas",
    )

    use_case = CreateSourceUseCase(source_repository=mock_repo)
    request = CreateSourceUseCase.InputData(
        name="cineplex",
        display_name="Cineplex",
        description="Cineplex cinemas",
    )

    response = await use_case.execute(request)

    assert response.name == "cineplex"
    assert response.display_name == "Cineplex"
    assert response.description == "Cineplex cinemas"
    mock_repo.find_by_name.assert_awaited_once()
    mock_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_source_raises_error_when_source_already_exists() -> None:
    """Verify duplicate name raises SourceAlreadyExistsError."""
    mock_repo = create_autospec(SourceDefinitionRepository, instance=True)
    existing = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
    )
    mock_repo.find_by_name.return_value = existing

    use_case = CreateSourceUseCase(source_repository=mock_repo)
    request = CreateSourceUseCase.InputData(name="cineplex", display_name="Cineplex")

    with pytest.raises(SourceAlreadyExistsError, match="already exists"):
        await use_case.execute(request)

    mock_repo.find_by_name.assert_awaited_once()
    mock_repo.save.assert_not_awaited()
