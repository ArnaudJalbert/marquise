"""Tests for the metadata refresh and merge command handlers."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from conftest import FactorySession, patch_factory_session, stub_factory
from marquise_cli import metadata_commands
from marquise_cli.helpers import console
from marquise_cli.metadata_commands import merge_apply, merge_preview, refresh


@pytest.fixture
def preview_file(tmp_path: Path) -> str:
    """A readable preview file for merge_apply."""
    path = tmp_path / "preview.json"
    path.write_text("{}")
    return str(path)


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> FactorySession:
    """Open every factory session over a stub factory."""
    return patch_factory_session(monkeypatch, stub_factory())


@pytest.fixture
def spinner() -> Iterator[MagicMock]:
    """Record the console spinner instead of drawing it."""
    with patch.object(console, "status", autospec=True) as status:
        yield status


@pytest.fixture
def stub_metadata_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the refresh and merge steps the handlers delegate to."""
    merge_result = MagicMock(status="preview")
    stubs = {
        "run_refresh_movies": 0,
        "dry_run_merge": merge_result,
        "apply_merge": merge_result,
        "format_merge": "",
    }
    for name, return_value in stubs.items():
        stub = create_autospec(
            getattr(metadata_commands, name), return_value=return_value
        )
        monkeypatch.setattr(metadata_commands, name, stub)


@pytest.mark.usefixtures("stub_metadata_steps")
@pytest.mark.parametrize(
    "handler",
    [
        pytest.param(lambda _: refresh(None, True), id="refresh"),
        pytest.param(lambda _: merge_preview("a", ["b"]), id="merge_preview"),
        pytest.param(lambda path: merge_apply("a", ["b"], path), id="merge_apply"),
    ],
)
def test_metadata_handlers_show_the_connecting_spinner(
    handler: Callable[[str], int],
    preview_file: str,
    session: FactorySession,
    spinner: MagicMock,
) -> None:
    """Each metadata handler opens its factory session behind the spinner."""
    handler(preview_file)

    spinner.assert_called_once_with("Connecting...", spinner="dots")
    assert session.closed
