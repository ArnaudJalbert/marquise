"""Tests for shared CLI helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from conftest import factory_session
from marquise_cli.helpers import connected_factory


@pytest.mark.asyncio
async def test_connected_factory_shuts_down_after_a_failure(
    mock_factory: MagicMock,
) -> None:
    """The factory shuts down when the command body raises."""
    with (
        patch(
            "marquise_cli.helpers.create_factory_session",
            factory_session(mock_factory),
        ),
        pytest.raises(RuntimeError, match="boom"),
    ):
        async with connected_factory() as factory:
            assert factory is mock_factory
            raise RuntimeError("boom")

    mock_factory.initialize.assert_awaited_once()
    mock_factory.shutdown.assert_awaited_once()
