"""CLI helper utilities — spinner, formatting, etc."""

from __future__ import annotations

from collections.abc import Awaitable

import questionary
from rich.console import Console

from marquise import ListCinemasUseCase, MarquiseFactory

_console = Console()


async def select_source(factory: MarquiseFactory, prompt: str) -> str | None:
    """Let the user pick a source interactively from a list."""
    list_sources_use_case = factory.list_sources_use_case
    response = await list_sources_use_case.execute(list_sources_use_case.InputData())
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


async def select_cinema(
    factory: MarquiseFactory,
    prompt: str,
) -> ListCinemasUseCase.CinemaData | None:
    """Let user select a cinema, or cancel."""
    list_cinemas_use_case = factory.list_cinemas_use_case
    response = await list_cinemas_use_case.execute(list_cinemas_use_case.InputData())
    if not response.cinemas:
        print("No cinemas available.")
        return None

    choices = [
        questionary.Choice(
            title=f"{cinema.name} — {cinema.address or 'No address'}, "
            f"{cinema.city or 'No city'}",
            value=cinema,
        )
        for cinema in response.cinemas
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
