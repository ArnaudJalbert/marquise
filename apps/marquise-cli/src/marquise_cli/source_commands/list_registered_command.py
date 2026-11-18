"""List registered showtime sources."""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.table import Table

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner, run_with_factory

_console = Console()


def _build_table(sources: list) -> Table:
    """Build registered-source table."""
    table = Table(title="Registered sources")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name")
    table.add_column("Description")
    for source in sources:
        table.add_row(source.name, source.display_name, source.description or "")
    return table


async def run_list_registered_sources(factory: MarquiseFactory) -> None:
    """List registered showtime sources in database."""
    list_sources_use_case = factory.sources.list_sources_use_case
    response = await run_spinner(
        list_sources_use_case.execute(list_sources_use_case.InputData()),
        description="Fetching registered sources...",
    )

    if not response.sources:
        print("No sources registered.")
        return

    _console.print(_build_table(response.sources))


def list_registered_sources() -> None:
    """List registered showtime sources in database."""
    asyncio.run(run_with_factory(run_list_registered_sources))
