"""Remove a cinema showtime-source assignment."""

from __future__ import annotations

import asyncio

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner, select_cinema


def unassign() -> None:
    """Remove showtime-source assignment from a cinema."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            selected = await select_cinema(
                factory, "Select a cinema to unassign a source from:"
            )
            if selected is None:
                return

            response = await run_spinner(
                factory.source.unassign_source(cinema_id=selected.id),
                description="Removing source assignment...",
            )
            print(f"Source unassigned from cinema {response.cinema_id}.")
        finally:
            await factory.shutdown()

    asyncio.run(_run())
