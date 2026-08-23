"""Unregister source definitions from database."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterable
from typing import Protocol

import questionary
from rich.console import Console
from rich.table import Table

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner

_console = Console()


class RegisteredSource(Protocol):
    """Registered source display data."""

    name: str
    display_name: str


def _build_table(
    sources: Iterable[RegisteredSource], registry_names: set[str]
) -> Table:
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


async def _select_sources(
    sources: Iterable[RegisteredSource],
) -> list[str] | None:
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
            await run_spinner(
                factory.source.delete_source(source_name=source_name),
                description=f"Removing {source_name}...",
            )
            print(f"  Removed: {source_name}")
        except Exception as error:
            print(f"  Failed: {error}", file=sys.stderr)


async def _unregister_sources(factory: MarquiseFactory) -> None:
    """Select and remove persistent source definitions."""
    registry_response = await run_spinner(
        factory.source.list_registry_sources(),
        description="Fetching available sources...",
    )
    registered_response = await run_spinner(
        factory.source.list_sources(), description="Fetching registered sources..."
    )
    if not registered_response.sources:
        print("No sources registered in the database.")
        return
    registry_names = {source.name for source in registry_response.sources}
    _console.print(_build_table(registered_response.sources, registry_names))
    selected = await _select_sources(registered_response.sources)
    if selected is not None:
        await _delete_sources(factory, selected)


def unregister_sources() -> None:
    """Remove selected showtime sources from database."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            await _unregister_sources(factory)
        finally:
            await factory.shutdown()

    asyncio.run(_run())
