"""Tests for ListAllCinemasUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import CinemaRepository, Page
from marquise.application.use_cases.list_all_cinemas import ListAllCinemasUseCase
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


@pytest.mark.asyncio
async def test_lists_every_matching_cinema_without_paging() -> None:
    """The name filter reaches the repository and no limit or offset is sent."""
    repository = create_autospec(CinemaRepository, instance=True)
    repository.find_all.return_value = Page(
        items=[Cinema(id=CinemaId(value="id-1"), name="Cinema A", city="Montreal")],
        total=1,
    )

    result = await ListAllCinemasUseCase(repository).execute(
        ListAllCinemasUseCase.InputData(name="Cinema")
    )

    repository.find_all.assert_awaited_once_with(name_filter="Cinema")
    assert result.cinemas == [
        ListAllCinemasUseCase.CinemaData(id="id-1", name="Cinema A", city="Montreal")
    ]


def test_input_rejects_a_blank_name() -> None:
    """A whitespace-only name filter is rejected before the repository is called."""
    with pytest.raises(ValueError, match="name must not be empty when provided"):
        ListAllCinemasUseCase.InputData(name="   ")
