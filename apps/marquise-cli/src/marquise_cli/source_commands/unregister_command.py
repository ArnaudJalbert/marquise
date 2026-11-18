"""Unregister source definitions from database."""

from __future__ import annotations

import asyncio
import sys

import questionary
from rich.table import Table

from marquise import MarquiseFactory, SourceNotFoundError
from marquise_cli.helpers import connected_factory, console, run_spinner


def _build_table(sources: list, registry_names: set[str]) -> Table:
    """Build persistent-source status table."""
    table = Table(title="Sources in database")
    table.add_column("Name", style="cyan")
    table.add_column("Status")
    for source in sources:
        table.add_row(
            source.name,
            "in registry" if source.name in registry_names else "not in registry",
        )
    return table


async def _select_sources(sources: list) -> list[str] | None:
    """Select source names to unregister."""
    selected = await questionary.checkbox(
        "Select sources to unregister:",
        choices=[
            questionary.Choice(
                title=f"{source.display_name} ({source.name})", value=source.name
            )
            for source in sources
        ],
    ).ask_async()
    if not selected:
        print("No sources selected.")
        return None
    confirmed = await questionary.confirm(
        f"Remove {len(selected)} source(s) from the database?", default=False
    ).ask_async()
    if not confirmed:
        print("Cancelled.")
        return None
    return selected


async def _delete_sources(factory: MarquiseFactory, source_names: list[str]) -> None:
    """Delete selected persistent source definitions."""
    for source_name in source_names:
        try:
            await _delete_source(factory, source_name)
        except SourceNotFoundError as error:
            print(f"  Failed: {error}", file=sys.stderr)
            raise SystemExit(1) from error


async def _delete_source(factory: MarquiseFactory, source_name: str) -> None:
    """Delete one source and report its successful removal."""
    delete_source_use_case = factory.delete_source_use_case
    await run_spinner(
        delete_source_use_case.execute(
            delete_source_use_case.InputData(source_name=source_name)
        ),
        description=f"Removing {source_name}...",
    )
    print(f"  Removed: {source_name}")


async def run_unregister_sources(factory: MarquiseFactory) -> None:
    """Select and remove persistent source definitions."""
    registry_use_case = factory.list_registry_sources_use_case
    registry_response = await run_spinner(
        registry_use_case.execute(registry_use_case.InputData()),
        description="Fetching available sources...",
    )
    list_use_case = factory.list_sources_use_case
    registered_response = await run_spinner(
        list_use_case.execute(list_use_case.InputData()),
        description="Fetching registered sources...",
    )
    if not registered_response.sources:
        print("No sources registered in the database.")
        return
    registry_names = {source.name for source in registry_response.sources}
    console.print(_build_table(registered_response.sources, registry_names))
    selected = await _select_sources(registered_response.sources)
    if selected is not None:
        await _delete_sources(factory, selected)


def unregister_sources() -> None:
    """Remove selected showtime sources from database."""

    async def run() -> None:
        async with connected_factory() as factory:
            await run_unregister_sources(factory)

    asyncio.run(run())
