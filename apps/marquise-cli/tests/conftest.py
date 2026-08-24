"""Shared fixtures and helpers for marquise-cli tests."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from marquise import ListCinemasUseCase
from marquise_cli.app import main


def invoke(args: list[str], input: str = "") -> SimpleNamespace:
    """Run CLI and capture process result."""
    stdout = StringIO()
    stderr = StringIO()
    with (
        patch("builtins.input", side_effect=input.splitlines()),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        try:
            exit_code = main(args)
        except SystemExit as error:
            exit_code = error.code or 0
    return SimpleNamespace(
        exit_code=exit_code,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for MarquiseFactory creation."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


@pytest.fixture
def mock_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory."""
    factory = MagicMock()
    factory.__aenter__ = AsyncMock(return_value=factory)
    factory.__aexit__ = AsyncMock(return_value=False)
    return factory


def make_cinema_data(
    cinema_id: str = "cin-001",
    name: str = "Test Cinema",
    address: str | None = "123 Test St",
    city: str | None = "Montreal",
    website: str | None = "https://example.com",
) -> ListCinemasUseCase.CinemaData:
    """Build a CinemaData instance for test setup."""
    return ListCinemasUseCase.CinemaData(
        id=cinema_id,
        name=name,
        address=address,
        city=city,
        website=website,
    )
