"""Tests for argparse CLI routing."""

from __future__ import annotations

import argparse
from unittest.mock import Mock

import pytest

from marquise_cli.auth_commands import invite, set_role
from marquise_cli.import_commands import import_cinema
from marquise_cli.routing import create_parser, dispatch


@pytest.mark.parametrize("group", ["cinema", "source", "import", "auth"])
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


def test_auth_commands_route_to_authorized_workflows() -> None:
    """Auth invite and set-role route to their account handlers."""
    invite_namespace = create_parser().parse_args(
        ["auth", "invite", "user@example.com", "--role", "member"]
    )
    role_namespace = create_parser().parse_args(
        ["auth", "set-role", "user@example.com", "--role", "editor"]
    )

    assert invite_namespace.handler is invite
    assert role_namespace.handler is set_role


def test_root_help_lists_command_groups(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Root help lists every supported command group."""
    with pytest.raises(SystemExit) as error:
        dispatch(create_parser(), ["--help"])

    assert error.value.code == 0
    output = capsys.readouterr().out
    assert "cinema" in output
    assert "source" in output
    assert "import" in output
    assert "auth" in output


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
        (["auth", "login"], "invalid choice"),
        (
            ["auth", "invite", "user@example.com", "--role", "owner"],
            "invalid choice",
        ),
        (
            ["auth", "set-role", "user@example.com", "--clear-role"],
            "required",
        ),
        (["auth", "set-role", "user@example.com"], "required"),
    ],
)
def test_invalid_paths_use_argparse_errors(
    argv: list[str],
    message: str,
    capsys: pytest.CaptureFixture[str],
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
    parser.set_defaults(
        handler=handler,
        handler_arguments=("days",),
        days=7,
    )

    assert dispatch(parser, []) == 0
    handler.assert_called_once_with(days=7)


def test_metadata_refresh_route_returns_handler_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A refresh failure reaches the shell as a nonzero exit code."""
    handler = Mock(return_value=1)
    monkeypatch.setattr("marquise_cli.routing.refresh", handler)
    assert dispatch(create_parser(), ["movie", "refresh", "--movie-id", "movie-1"]) == 1
    handler.assert_called_once_with(movie_id="movie-1", all_movies=False)


def test_guarded_merge_routes_require_a_preview_file() -> None:
    """Apply requires the exact preview to be supplied by the operator."""
    with pytest.raises(SystemExit):
        create_parser().parse_args(["movie", "merge-apply", "keep", "duplicate"])
    args = create_parser().parse_args(
        ["movie", "merge-apply", "keep", "duplicate", "--preview-file", "preview.json"]
    )
    assert args.survivor_id == "keep"
    assert args.duplicate_ids == ["duplicate"]
    assert args.preview_file == "preview.json"
