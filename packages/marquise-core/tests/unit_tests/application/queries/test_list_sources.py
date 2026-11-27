"""Tests for ListSourcesQuery."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.queries.list_sources import ListSourcesQuery
from marquise.application.readers import SourceDefinitionReader


@pytest.mark.asyncio
async def test_list_sources_returns_reader_data() -> None:
    """Every registered source comes back as the reader returned it."""
    reader = create_autospec(SourceDefinitionReader, instance=True)
    expected = [
        SourceDefinitionReader.SourceDefinitionData(
            name="cineplex", display_name="Cineplex", description="Cineplex cinemas"
        ),
        SourceDefinitionReader.SourceDefinitionData(
            name="cinema_du_parc", display_name="Cinema du Parc", description=None
        ),
    ]
    reader.list_all.return_value = expected
    query = ListSourcesQuery(source_definition_reader=reader)

    response = await query.execute(ListSourcesQuery.InputData())

    assert response.sources == expected
    reader.list_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_sources_returns_empty_list() -> None:
    """No registered sources gives an empty list."""
    reader = create_autospec(SourceDefinitionReader, instance=True)
    reader.list_all.return_value = []
    query = ListSourcesQuery(source_definition_reader=reader)

    response = await query.execute(ListSourcesQuery.InputData())

    assert response.sources == []
