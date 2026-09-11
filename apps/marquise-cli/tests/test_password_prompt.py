"""Tests for masked password prompting."""

from __future__ import annotations

from unittest.mock import patch

from marquise_cli.helpers import prompt_password


def test_prompt_password_returns_masked_typed_value() -> None:
    """Password prompt returns the typed password without echoing it."""
    with patch("marquise_cli.helpers.questionary.password") as password:
        password.return_value.ask.return_value = "s3cr3t"

        value = prompt_password("Password: ")

    assert value == "s3cr3t"
    password.assert_called_once_with("Password: ")


def test_prompt_password_returns_empty_on_cancel() -> None:
    """Cancelling the prompt yields an empty string, never None."""
    with patch("marquise_cli.helpers.questionary.password") as password:
        password.return_value.ask.return_value = None

        value = prompt_password("Password: ")

    assert value == ""
