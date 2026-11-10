"""The CLI offers import commands and no account administration."""

from __future__ import annotations

import pytest

from marquise_cli.app import main


def test_help_lists_import_and_omits_auth(capsys: pytest.CaptureFixture[str]) -> None:
    """Top-level help shows the import group and no auth group."""
    with pytest.raises(SystemExit) as error:
        main(["--help"])

    help_text = capsys.readouterr().out
    assert error.value.code == 0
    assert "import" in help_text
    assert "auth" not in help_text


@pytest.mark.parametrize(
    "argv",
    [
        ["auth", "invite", "user@example.com", "--role", "editor"],
        ["auth", "set-role", "user@example.com", "--role", "member"],
    ],
)
def test_auth_commands_fail_as_unsupported(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """Former auth commands exit with a usage error naming the invalid choice."""
    with pytest.raises(SystemExit) as error:
        main(argv)

    assert error.value.code == 2
    assert "invalid choice: 'auth'" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["cinema", "all"])
def test_import_commands_remain_available(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each import command still prints its help."""
    with pytest.raises(SystemExit) as error:
        main(["import", command, "--help"])

    assert error.value.code == 0
    assert f"usage: marquise import {command}" in capsys.readouterr().out
