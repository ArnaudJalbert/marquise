"""CLI helper utilities — spinner, formatting, etc."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TypeVar

from rich.console import Console

T = TypeVar("T")

_console = Console()


async def run_spinner(coro: Awaitable[T], description: str = "Working") -> T:
    """Execute an awaitable while displaying a spinner animation.

    Args:
        coro: The awaitable to execute.
        description: Text to display alongside the spinner.

    Returns:
        The result of the awaitable.
    """
    with _console.status(description, spinner="dots"):
        return await coro
