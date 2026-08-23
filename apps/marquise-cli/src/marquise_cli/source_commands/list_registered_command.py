"""List registered showtime sources."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Protocol

from rich.console import Console
from rich.table import Table

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner

_console = Console()


class RegisteredSource(Protocol):
    """Registered source display data."""

    name: str
    display_name: str
    description: str | None


def _build_table(sources: Iterable[RegisteredSource]) -> Table:
    """Build registered-source table."""
    table = Table(title="Registered sources")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name")
    table.add_column("Description")
    for source in sources:
        table.add_row(source.name, source.display_name, source.description or "")
    return table


def list_registered_sources() -> None:
    """List registered showtime sources in database."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            response = await run_spinner(
                factory.source.list_sources(),
                description="Fetching registered sources...",
            )
        finally:
            await factory.shutdown()

        if not response.sources:
            print("No sources registered.")
            return

        _console.print(_build_table(response.sources))

    asyncio.run(_run())
