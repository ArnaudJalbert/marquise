"""Tests for argparse CLI routing."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from marquise import ReconcileScreeningsCommand, ScreeningNotFoundError
from marquise_cli.data_commands import audit, reconcile, run_reconcile
from marquise_cli.import_commands import import_cinema
from marquise_cli.routing import create_parser, dispatch


@pytest.mark.parametrize("group", ["cinema", "source", "import", "data"])
def test_group_help(group: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Each top-level command group prints argparse help."""
    with pytest.raises(SystemExit) as error:
        dispatch(create_parser(), [group, "--help"])

    assert error.value.code == 0
    assert f"usage: marquise {group}" in capsys.readouterr().out


def test_import_cinema_routes_to_single_cinema_handler() -> None:
    """Interactive cinema import is nested under the import command group."""
    namespace = create_parser().parse_args(["import", "cinema"])

    assert namespace.handler is import_cinema


def test_data_commands_route_to_reliability_handlers() -> None:
    """Audit and reconcile are exposed under the data command group."""
    assert create_parser().parse_args(["data", "audit"]).handler is audit
    namespace = create_parser().parse_args(["data", "reconcile", "plan.json"])
    assert namespace.handler is reconcile
    assert namespace.apply is False


def test_root_help_lists_command_groups(capsys: pytest.CaptureFixture[str]) -> None:
    """Root help lists every supported command group."""
    with pytest.raises(SystemExit) as error:
        dispatch(create_parser(), ["--help"])

    assert error.value.code == 0
    output = capsys.readouterr().out
    assert "cinema" in output
    assert "source" in output
    assert "import" in output


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        ([], "the following arguments are required"),
        (["unknown"], "invalid choice"),
        (["cinema"], "the following arguments are required"),
        (["cinema", "unknown"], "invalid choice"),
        (["source", "list-assignments"], "invalid choice"),
        (["source", "import"], "invalid choice"),
        (["import", "all", "--days", "0"], "must be greater than zero"),
    ],
)
def test_invalid_paths_use_argparse_errors(
    argv: list[str], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing and invalid arguments use argparse errors."""
    with pytest.raises(SystemExit) as error:
        dispatch(create_parser(), argv)

    assert error.value.code == 2
    assert message in capsys.readouterr().err


def test_dispatch_passes_parsed_arguments_to_handler() -> None:
    """Dispatch invokes handler with registered parser arguments."""
    handler = Mock()
    parser = argparse.ArgumentParser()
    parser.set_defaults(handler=handler, handler_arguments=("days",), days=7)

    assert dispatch(parser, []) == 0
    handler.assert_called_once_with(days=7)


@pytest.mark.asyncio
async def test_reconcile_cli_prints_not_found_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing screening is reported as JSON rather than a traceback."""

    class MissingRepository:
        async def find_by_id(self, _screening_id: str) -> None:
            raise ScreeningNotFoundError("missing")

    plan = tmp_path / "plan.json"
    plan.write_text(
        '[{"screening_id": "missing", "ticket_url": "https://example.test"}]'
    )
    factory = SimpleNamespace(
        initialize=AsyncMock(),
        shutdown=AsyncMock(),
        reconcile_screenings_command=ReconcileScreeningsCommand(MissingRepository()),
    )

    await run_reconcile(factory, str(plan), False, None)

    captured = capsys.readouterr()
    assert "not-found" in captured.out
    assert captured.err == ""
