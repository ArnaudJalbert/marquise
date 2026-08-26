"""Remove a cinema showtime-source assignment."""

from __future__ import annotations

import asyncio

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner, select_cinema


async def run_unassign(factory: MarquiseFactory) -> None:
    """Remove showtime-source assignment from a cinema."""
    await run_spinner(factory.initialize(), description="Connecting...")
    try:
        selected = await select_cinema(
            factory, "Select a cinema to unassign a source from:"
        )
        if selected is None:
            return

        unassign_source_use_case = factory.unassign_source_use_case
        response = await run_spinner(
            unassign_source_use_case.execute(
                unassign_source_use_case.InputData(cinema_id=selected.id)
            ),
            description="Removing source assignment...",
        )
        print(f"Source unassigned from cinema {response.cinema_id}.")
    finally:
        await factory.shutdown()


def unassign() -> None:
    """Remove showtime-source assignment from a cinema."""
    asyncio.run(run_unassign(MarquiseFactory()))
