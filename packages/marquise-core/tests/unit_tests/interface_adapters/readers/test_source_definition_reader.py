"""Unit tests for the source definition display adapter."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.readers import SourceDefinitionReader
from marquise.interface_adapters.readers.source_definition_read_gateway import (
    SourceDefinitionReadGateway,
)
from marquise.interface_adapters.readers.source_definition_reader import (
    PostgresSourceDefinitionReader,
)


@pytest.mark.asyncio
async def test_list_all_maps_gateway_rows_in_order() -> None:
    """Each gateway row becomes one source definition display record, in order."""
    gateway = create_autospec(SourceDefinitionReadGateway, instance=True)
    gateway.list_all.return_value = [
        {"name": "cineplex", "display_name": "Cineplex", "description": "Chain"},
        {"name": "parc", "display_name": "Cinema du Parc", "description": None},
    ]

    result = await PostgresSourceDefinitionReader(gateway=gateway).list_all()

    assert result == [
        SourceDefinitionReader.SourceDefinitionData(
            name="cineplex", display_name="Cineplex", description="Chain"
        ),
        SourceDefinitionReader.SourceDefinitionData(
            name="parc", display_name="Cinema du Parc", description=None
        ),
    ]
    gateway.list_all.assert_awaited_once_with()
