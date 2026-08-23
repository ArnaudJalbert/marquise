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


def _build_table(registry_sources: object, registered_names: set[str]) -> Table:
    """Build registry registration-status table."""
    table = Table(title="Sources available in registry")
    table.add_column("Name", style="cyan")
    table.add_column("Status")
    for source in registry_sources:
        table.add_row(
            source.name,
            "already registered" if source.name in registered_names else "new",
        )
    return table


async def _source_details() -> tuple[str, str | None] | None:
    """Prompt for source display data."""
    display_name = await questionary.text("Display name:").ask_async()
    if display_name is None:
        print("Cancelled.")
        return None
    description = await questionary.text("Description (optional):").ask_async()
    if description is None:
        print("Cancelled.")
        return None
    return display_name, description if description.strip() else None


async def _register_sources(factory: MarquiseFactory) -> None:
    """Register every source missing from persistent source definitions."""
    registry_response = await run_spinner(
        factory.source.list_registry_sources(),
        description="Fetching available sources...",
    )
    registered_response = await run_spinner(
        factory.source.list_sources(), description="Fetching registered sources..."
    )
    registered_names = {source.name for source in registered_response.sources}
    new_sources = [
        source
        for source in registry_response.sources
        if source.name not in registered_names
    ]
    if not registry_response.sources:
        print("No sources available in the registry.")
        return

    _console.print(_build_table(registry_response.sources, registered_names))
    if not new_sources:
        print("All registry sources are already in the database.")
        return

    print(f"{len(new_sources)} source(s) can be registered.")
    for source in new_sources:
        print(f"\n--- Registering: {source.name} ---")
        details = await _source_details()
        if details is None:
            return
        display_name, description = details
        try:
            result = await run_spinner(
                factory.source.create_source(
                    name=source.name, display_name=display_name, description=description
                ),
                description=f"Registering {source.name}...",
            )
            print(f"  Created: {result.name}")
        except Exception as error:
            print(f"  Failed: {error}", file=sys.stderr)


def register_sources() -> None:
    """Register new showtime sources from registry into database."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            await _register_sources(factory)
        finally:
            await factory.shutdown()

    asyncio.run(_run())
