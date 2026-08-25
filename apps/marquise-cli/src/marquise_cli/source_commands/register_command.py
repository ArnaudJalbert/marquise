"""Register source adapters in database."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict

import questionary
from rich.console import Console
from rich.table import Table

from marquise import (
    CreateSourceUseCase,
    ListRegistrySourcesUseCase,
    ListSourcesUseCase,
    MarquiseFactory,
)
from marquise_cli.helpers import run_spinner

_console = Console()


def _build_table(registry_sources: list, registered_names: set[str]) -> Table:
    """Build registry registration-status table."""
    table = Table(title="Sources available in registry")
    table.add_column("Name", style="cyan")
    table.add_column("Status")
    for source in registry_sources:
        table.add_row(
            source["name"],
            "already registered" if source["name"] in registered_names else "new",
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


async def _load_sources(
    factory: MarquiseFactory,
) -> tuple[list, list]:
    """Load registry and registered source definitions."""
    registry_use_case = factory.list_registry_sources_use_case
    registry_response = await run_spinner(
        registry_use_case.execute(ListRegistrySourcesUseCase.InputData()),
        description="Fetching available sources...",
    )
    list_use_case = factory.list_sources_use_case
    registered_response = await run_spinner(
        list_use_case.execute(ListSourcesUseCase.InputData()),
        description="Fetching registered sources...",
    )
    return (
        [asdict(source) for source in registry_response.sources],
        [asdict(source) for source in registered_response.sources],
    )


async def _register_source(factory: MarquiseFactory, source: dict) -> bool:
    """Prompt for and register one source definition."""
    print(f"\n--- Registering: {source['name']} ---")
    details = await _source_details()
    if details is None:
        return False
    display_name, description = details
    try:
        use_case = factory.create_source_use_case
        result = await run_spinner(
            use_case.execute(
                CreateSourceUseCase.InputData(
                    name=source["name"],
                    display_name=display_name,
                    description=description,
                )
            ),
            description=f"Registering {source['name']}...",
        )
        print(f"  Created: {result.name}")
    except Exception as error:
        print(f"  Failed: {error}", file=sys.stderr)
    return True


async def run_register_sources(factory: MarquiseFactory) -> None:
    """Register every source missing from persistent source definitions."""
    await run_spinner(factory.initialize(), description="Connecting...")
    try:
        registry_sources, registered_sources = await _load_sources(factory)
        registered_names = {source["name"] for source in registered_sources}
        new_sources = [
            source
            for source in registry_sources
            if source["name"] not in registered_names
        ]
        if not registry_sources:
            print("No sources available in the registry.")
            return

        _console.print(_build_table(registry_sources, registered_names))
        if not new_sources:
            print("All registry sources are already in the database.")
            return

        print(f"{len(new_sources)} source(s) can be registered.")
        for source in new_sources:
            if not await _register_source(factory, source):
                return
    finally:
        await factory.shutdown()


def register_sources() -> None:
    """Register new showtime sources from registry into database."""
    asyncio.run(run_register_sources(MarquiseFactory()))
