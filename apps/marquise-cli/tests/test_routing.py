"""Tests for argparse CLI routing."""

from __future__ import annotations

import argparse
from unittest.mock import Mock

import pytest

from marquise_cli.routing import create_parser, dispatch


@pytest.mark.parametrize("group", ["cinema", "source", "import"])
def test_group_help(group: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Each top-level command group prints argparse help."""
    with pytest.raises(SystemExit) as error:
        dispatch(create_parser(), [group, "--help"])

    assert error.value.code == 0
    assert f"usage: marquise {group}" in capsys.readouterr().out


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
