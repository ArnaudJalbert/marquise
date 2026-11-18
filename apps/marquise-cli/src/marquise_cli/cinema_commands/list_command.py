"""Cinema listing CLI command."""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

from rich import box
from rich.table import Table
from rich.text import Text

from marquise import ListCinemasUseCase, MarquiseFactory
from marquise_cli.helpers import connected_factory, console, run_spinner


def _website_text(website: str) -> Text:
    """Return a safe website hyperlink or invalid URL label."""
    if any(ord(character) < 32 or ord(character) == 127 for character in website):
        return Text("Invalid URL", style="dim")
    try:
        parsed = urlsplit(website)
    except ValueError:
        return Text("Invalid URL", style="dim")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return Text("Invalid URL", style="dim")
    return Text(website, style=f"blue underline link {website}")


def _build_table(
    response: ListCinemasUseCase.OutputData,
    source_names: dict[str, str],
    verbose: bool,
) -> Table:
    """Build cinema list table."""
    table = Table(
        title="Available cinemas",
        box=box.ROUNDED,
        header_style="bold",
        show_lines=True,
    )
    table.add_column("Cinema", style="cyan", no_wrap=True)
    table.add_column("City", style="magenta")
    if verbose:
        table.add_column("Address", style="green", overflow="fold")
        table.add_column("Website", style="blue underline", overflow="fold")
        table.add_column("Source", style="yellow", overflow="fold")
        table.add_column("ID", style="dim")

    for cinema in response.cinemas:
        row: list[str | Text] = [cinema.name, cinema.city or "-"]
        if verbose:
            row.extend(
                [
                    cinema.address or "-",
                    _website_text(cinema.website) if cinema.website else "-",
                    source_names.get(cinema.id, ""),
                    cinema.id,
                ]
            )
        table.add_row(*row)
    return table


async def run_list_cinemas(
    factory: MarquiseFactory,
    *,
    name: str | None = None,
    verbose: bool = False,
) -> None:
    """List all available cinemas."""
    list_cinemas_use_case = factory.list_cinemas_use_case
    response = await run_spinner(
        list_cinemas_use_case.execute(list_cinemas_use_case.InputData(name=name)),
        description="Fetching cinemas...",
    )
    if not response.cinemas:
        print("No cinemas found.")
        return

    source_names: dict[str, str] = {}
    if verbose:
        query = factory.list_cinema_source_assignments_query
        assignments = await run_spinner(
            query.execute(query.InputData()),
            description="Fetching source assignments...",
        )
        source_names = {
            assignment.cinema_id: assignment.source_display_name
            for assignment in assignments.assignments
        }

    console.print(_build_table(response, source_names, verbose))


def list_cinemas(
    name: str | None = None,
    verbose: bool = False,
) -> None:
    """List all available cinemas."""

    async def run() -> None:
        async with connected_factory() as factory:
            await run_list_cinemas(factory, name=name, verbose=verbose)

    asyncio.run(run())
