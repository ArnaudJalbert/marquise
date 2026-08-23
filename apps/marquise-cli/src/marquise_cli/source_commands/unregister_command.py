"""Unregister source definitions from database."""

from __future__ import annotations

import asyncio
import sys

import questionary
from rich.console import Console
from rich.table import Table

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner

_console = Console()


def unregister_sources() -> None:
    """Remove selected showtime sources from database."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            registry_response = await run_spinner(
                factory.source.list_registry_sources(),
                description="Fetching available sources...",
            )
            db_response = await run_spinner(
                factory.source.list_sources(),
                description="Fetching registered sources...",
            )
            if not db_response.sources:
                print("No sources registered in the database.")
                return

            registry_names = {source.name for source in registry_response.sources}
            table = Table(title="Sources in database")
            table.add_column("Name", style="cyan")
            table.add_column("Status")
            for source in db_response.sources:
                table.add_row(
                    source.name,
                    "in registry"
                    if source.name in registry_names
                    else "not in registry",
                )
            _console.print(table)

            selected = await questionary.checkbox(
                "Select sources to unregister:",
                choices=[
                    questionary.Choice(
                        title=f"{source.display_name} ({source.name})",
                        value=source.name,
                    )
                    for source in db_response.sources
                ],
            ).ask_async()
            if not selected:
                print("No sources selected.")
                return

            confirmed = await questionary.confirm(
                f"Remove {len(selected)} source(s) from the database?",
                default=False,
            ).ask_async()
            if not confirmed:
                print("Cancelled.")
                return

            for source_name in selected:
                try:
                    await run_spinner(
                        factory.source.delete_source(source_name=source_name),
                        description=f"Removing {source_name}...",
                    )
                    print(f"  Removed: {source_name}")
                except Exception as error:
                    print(f"  Failed: {error}", file=sys.stderr)
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as error:
        print(f"Failed to unregister sources: {error}", file=sys.stderr)
        raise SystemExit(1) from error
