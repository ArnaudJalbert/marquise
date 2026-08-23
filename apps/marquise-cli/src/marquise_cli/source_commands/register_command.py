"""Register source adapters in database."""

from __future__ import annotations

import asyncio
import sys

import questionary
from rich.console import Console
from rich.table import Table

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner

_console = Console()


def register_sources() -> None:
    """Register new showtime sources from registry into database."""
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
            db_names = {source.name for source in db_response.sources}
            new_sources = [
                source
                for source in registry_response.sources
                if source.name not in db_names
            ]

            if not registry_response.sources:
                print("No sources available in the registry.")
                return

            table = Table(title="Sources available in registry")
            table.add_column("Name", style="cyan")
            table.add_column("Status")
            for source in registry_response.sources:
                table.add_row(
                    source.name,
                    "already registered" if source.name in db_names else "new",
                )
            _console.print(table)

            if not new_sources:
                print("All registry sources are already in the database.")
                return

            print(f"{len(new_sources)} source(s) can be registered.")
            for source in new_sources:
                print(f"\n--- Registering: {source.name} ---")
                display_name = await questionary.text("Display name:").ask_async()
                if display_name is None:
                    print("Cancelled.")
                    return

                description = await questionary.text(
                    "Description (optional):"
                ).ask_async()
                if description is None:
                    print("Cancelled.")
                    return

                try:
                    result = await run_spinner(
                        factory.source.create_source(
                            name=source.name,
                            display_name=display_name,
                            description=description if description.strip() else None,
                        ),
                        description=f"Registering {source.name}...",
                    )
                    print(f"  Created: {result.name}")
                except Exception as error:
                    print(f"  Failed: {error}", file=sys.stderr)
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as error:
        print(f"Failed to register sources: {error}", file=sys.stderr)
        raise SystemExit(1) from error
