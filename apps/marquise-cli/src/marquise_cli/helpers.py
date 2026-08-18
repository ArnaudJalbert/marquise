"""CLI helper utilities — spinner, formatting, etc."""

from __future__ import annotations

from collections.abc import Awaitable

import questionary
from rich.console import Console

from marquise import MarquiseFactory

_console = Console()


async def select_source(factory: MarquiseFactory, prompt: str) -> str | None:
    """Let the user pick a source interactively from a list."""
    response = await factory.source.list_sources()
    if not response.sources:
        print("No sources available.")
        return None

    choices = [
        questionary.Choice(
            title=f"{source.display_name} ({source.name})",
            value=source.name,
        )
        for source in response.sources
    ]
    choices.append(questionary.Choice(title="← exit", value="__exit__"))

    selected = await questionary.select(prompt, choices=choices).ask_async()
    if selected is None or selected == "__exit__":
        print("Cancelled.")
        return None
    return selected


async def run_spinner[T](coro: Awaitable[T], description: str = "Working") -> T:
    """Execute an awaitable while displaying a spinner animation.

    Args:
        coro: The awaitable to execute.
        description: Text to display alongside the spinner.

    Returns:
        The result of the awaitable.
    """
    with _console.status(description, spinner="dots"):
        return await coro
