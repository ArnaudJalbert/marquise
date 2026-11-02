"""Screening write transaction contract owns its types."""

import ast
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from marquise.application.transactions import screening_write
from marquise.application.transactions.screening_write import ScreeningWriteResult


def test_port_imports_no_use_case_module() -> None:
    """The port cannot depend on, or loop back into, any use case module."""
    tree = ast.parse(Path(screening_write.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any("use_cases" in (name or "") for name in imported)


def test_result_keeps_persisted_replay_shape() -> None:
    """Replays committed before the port owned its type still map field-for-field."""
    result = ScreeningWriteResult(
        screening_id="scr-1",
        changed=True,
        screening=ScreeningWriteResult.Screening(
            id="scr-1",
            movie_id="mov-1",
            movie_title="Movie One",
            cinema_id="cin-1",
            cinema_name="Cinema One",
            showtime=datetime(2026, 10, 7, 12, tzinfo=UTC),
        ),
    )
    data = asdict(result)
    assert set(data) == {"screening_id", "changed", "screening"}
    assert set(data["screening"]) == {
        "id",
        "movie_id",
        "movie_title",
        "cinema_id",
        "cinema_name",
        "showtime",
        "ticket_url",
        "room",
        "language",
    }
