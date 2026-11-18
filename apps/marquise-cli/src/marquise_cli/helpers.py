"""CLI helper utilities — spinner, formatting, etc."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import questionary
from rich.console import Console

from marquise import ListCinemasUseCase, MarquiseFactory, create_factory_session

_console = Console()

_CINEMAS_PER_PAGE = 100


async def run_with_factory[T](
    command: Callable[[MarquiseFactory], Awaitable[T]],
) -> T:
    """Run a command inside one factory session, then close the database.

    Args:
        command: Coroutine function that receives the open factory.

    Returns:
        The command's result.
    """
    async with create_factory_session() as factory:
        return await command(factory)


async def list_every_cinema(
    factory: MarquiseFactory, name: str | None
) -> list[ListCinemasUseCase.CinemaData]:
    """Read every cinema matching the name filter, one page at a time.

    Args:
        factory: The open factory.
        name: Name filter, or None for every cinema.

    Returns:
        Every matching cinema, in repository order.
    """
    use_case = factory.cinemas.list_cinemas_use_case
    cinemas: list[ListCinemasUseCase.CinemaData] = []
    page = 1
    while True:
        output = await _read_cinema_page(use_case, page, name)
        cinemas.extend(output.cinemas)
        if not output.cinemas or len(cinemas) >= output.total:
            return cinemas
        page += 1


async def _read_cinema_page(
    use_case: ListCinemasUseCase, page: int, name: str | None
) -> ListCinemasUseCase.OutputData:
    return await use_case.execute(
        use_case.InputData(page=page, size=_CINEMAS_PER_PAGE, name=name)
    )


async def select_source(factory: MarquiseFactory, prompt: str) -> str | None:
    """Let the user pick a source interactively from a list."""
    list_sources_use_case = factory.sources.list_sources_use_case
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
    cinemas = await list_every_cinema(factory, name=None)
    if not cinemas:
        print("No cinemas available.")
        return None

    choices = [
        questionary.Choice(
            title=f"{cinema.name} — {cinema.address or 'No address'}, "
            f"{cinema.city or 'No city'}",
            value=cinema,
        )
        for cinema in cinemas
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
