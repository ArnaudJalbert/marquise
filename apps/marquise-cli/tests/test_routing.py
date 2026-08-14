"""Tests for argparse CLI routing."""

from __future__ import annotations

import argparse
from unittest.mock import Mock, patch

import pytest

from marquise_cli.app import main
from marquise_cli.routing import create_parser, dispatch


@pytest.mark.parametrize("group", ["cinema", "source", "import"])
def test_group_help(group: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Each top-level command group prints argparse help."""
    parser = create_parser(Mock(return_value=0))

    with pytest.raises(SystemExit) as error:
        dispatch(parser, [group, "--help"])

    assert error.value.code == 0
    assert f"usage: marquise {group}" in capsys.readouterr().out


def test_root_help_lists_command_groups(capsys: pytest.CaptureFixture[str]) -> None:
    """Root help lists every supported command group."""
    parser = create_parser(Mock(return_value=0))

    with pytest.raises(SystemExit) as error:
        dispatch(parser, ["--help"])

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
    ],
)
def test_invalid_paths_use_argparse_errors(
    argv: list[str], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing and unknown paths use argparse's standard error exit code."""
    parser = create_parser(Mock(return_value=0))

    with pytest.raises(SystemExit) as error:
        dispatch(parser, argv)

    assert error.value.code == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["cinema", "list", "--verbose"], ("cinema", "list", ["--verbose"])),
        (["source", "import", "--days", "7"], ("source", "import", ["--days", "7"])),
        (["import", "all", "--days", "7"], ("import", "all", ["--days", "7"])),
    ],
)
def test_fallback_receives_unmodified_leaf_arguments(
    argv: list[str], expected: tuple[str, str, list[str]]
) -> None:
    """Fallback receives group, command, and original option tokens."""
    fallback = Mock(return_value=0)

    assert dispatch(create_parser(fallback), argv) == 0

    namespace = fallback.call_args.args[0]
    assert (namespace.group, namespace.command, namespace.args) == expected


def test_dispatch_runs_async_handler() -> None:
    """Dispatch runs an async command handler and returns its exit code."""
    parser = argparse.ArgumentParser()

    async def handler(namespace: argparse.Namespace) -> int:
        """Return command success code."""
        assert isinstance(namespace, argparse.Namespace)
        return 3

    parser.set_defaults(handler=handler)

    assert dispatch(parser, []) == 3


def test_main_delegates_unmigrated_command_to_typer() -> None:
    """Main routes an unmigrated leaf command through existing Typer app."""
    with patch("marquise_cli.app.app") as typer_app:
        assert main(["cinema", "list", "--verbose"]) == 0

    typer_app.assert_called_once_with(args=["cinema", "list", "--verbose"])
