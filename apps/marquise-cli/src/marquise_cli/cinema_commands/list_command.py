"""Cinema listing CLI command."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from functools import partial
from urllib.parse import urlsplit

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from marquise import ListAllCinemasUseCase, MarquiseFactory
from marquise_cli.helpers import run_spinner, run_with_factory

_console = Console(markup=False)


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
    response: ListAllCinemasUseCase.OutputData,
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

    for cinema in map(asdict, response.cinemas):
        row: list[str | Text] = [cinema["name"], cinema["city"] or "-"]
        if verbose:
            row.extend(
                [
                    cinema["address"] or "-",
                    _website_text(cinema["website"]) if cinema["website"] else "-",
                    source_names.get(cinema["id"], ""),
                    cinema["id"],
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
    list_cinemas_use_case = factory.cinemas.list_all_cinemas_use_case
    response = await run_spinner(
        list_cinemas_use_case.execute(list_cinemas_use_case.InputData(name=name)),
        description="Fetching cinemas...",
    )
    if not response.cinemas:
        print("No cinemas found.")
        return

    source_names: dict[str, str] = {}
    if verbose:
        query = factory.sources.list_cinema_source_assignments_query
        assignments = await run_spinner(
            query.execute(query.InputData()),
            description="Fetching source assignments...",
        )
        source_names = {
            assignment.cinema_id: assignment.source_display_name
            for assignment in assignments.assignments
        }

    _console.print(_build_table(response, source_names, verbose))


def list_cinemas(
    name: str | None = None,
    verbose: bool = False,
) -> None:
    """List all available cinemas."""
    asyncio.run(run_with_factory(partial(run_list_cinemas, name=name, verbose=verbose)))
