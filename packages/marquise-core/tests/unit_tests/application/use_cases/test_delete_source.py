"""Tests for DeleteSourceUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import SourceNotFoundError
from marquise.application.repositories import SourceDefinitionRepository
from marquise.application.use_cases import DeleteSourceUseCase


@pytest.mark.asyncio
async def test_delete_source_deletes_and_returns_name() -> None:
    """Verify delete removes the source and returns the name."""
    mock_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_repo.delete.return_value = True

    use_case = DeleteSourceUseCase(source_repository=mock_repo)
    request = DeleteSourceUseCase.InputData(source_name="cineplex")

    response = await use_case.execute(request)

    assert response.source_name == "cineplex"
    mock_repo.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_source_raises_not_found() -> None:
    """Verify delete raises SourceNotFoundError when source is missing."""
    mock_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_repo.delete.return_value = False

    use_case = DeleteSourceUseCase(source_repository=mock_repo)
    request = DeleteSourceUseCase.InputData(source_name="missing")

    with pytest.raises(SourceNotFoundError, match="was not found"):
        await use_case.execute(request)

    mock_repo.delete.assert_awaited_once()
