"""Tests for the metadata refresh and merge command handlers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest import factory_session
from marquise_cli.metadata_commands import merge_apply, merge_preview, refresh


@pytest.fixture
def preview_file(tmp_path: Path) -> str:
    """A readable preview file for merge_apply."""
    path = tmp_path / "preview.json"
    path.write_text("{}")
    return str(path)


@pytest.mark.parametrize(
    "handler_name",
    ["refresh", "merge_preview", "merge_apply"],
)
def test_metadata_handlers_show_the_connecting_spinner(
    handler_name: str, preview_file: str
) -> None:
    """Each metadata handler opens its factory session behind the spinner."""
    factory = MagicMock()
    factory.initialize = AsyncMock()
    factory.shutdown = AsyncMock()
    handlers: dict[str, Callable[[], int]] = {
        "refresh": lambda: refresh(None, True),
        "merge_preview": lambda: merge_preview("a", ["b"]),
        "merge_apply": lambda: merge_apply("a", ["b"], preview_file),
    }
    merge_result = MagicMock(status="preview")

    with (
        patch("marquise_cli.helpers.create_factory_session", factory_session(factory)),
        patch("marquise_cli.helpers.console.status") as status,
        patch(
            "marquise_cli.metadata_commands.run_refresh_movies",
            AsyncMock(return_value=0),
        ),
        patch(
            "marquise_cli.metadata_commands.dry_run_merge",
            AsyncMock(return_value=merge_result),
        ),
        patch(
            "marquise_cli.metadata_commands.apply_merge",
            AsyncMock(return_value=merge_result),
        ),
        patch("marquise_cli.metadata_commands.format_merge", return_value=""),
    ):
        handlers[handler_name]()

    status.assert_called_once_with("Connecting...", spinner="dots")
    factory.shutdown.assert_awaited_once()
