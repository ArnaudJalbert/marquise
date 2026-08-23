"""List registered showtime sources."""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console
from rich.table import Table

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner

_console = Console()


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

        table = Table(title="Registered sources")
        table.add_column("Name", style="cyan")
        table.add_column("Display Name")
        table.add_column("Description")
        for source in response.sources:
            table.add_row(source.name, source.display_name, source.description or "")
        _console.print(table)

    try:
        asyncio.run(_run())
    except Exception as error:
        print(f"Failed to list sources: {error}", file=sys.stderr)
        raise SystemExit(1) from error
