"""Assign a showtime source to a cinema."""

from __future__ import annotations

import asyncio
import sys

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner, select_cinema, select_source


def assign() -> None:
    """Assign a showtime source to a cinema after interactive selection."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            selected = await select_cinema(
                factory, "Select a cinema to assign a source to:"
            )
            if selected is None:
                return

            source_name = await select_source(factory, "Select a source to assign:")
            if source_name is None:
                return

            response = await run_spinner(
                factory.source.assign_source(
                    cinema_id=selected.id,
                    source_name=source_name,
                ),
                description="Assigning source...",
            )
            print("Source assigned:")
            print(f"  Cinema:      {response.cinema_id}")
            print(f"  Source:      {response.source_name}")
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as error:
        print(f"Failed to assign source: {error}", file=sys.stderr)
        raise SystemExit(1) from error
