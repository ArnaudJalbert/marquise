"""Remove a cinema showtime-source assignment."""

from __future__ import annotations

import asyncio
import sys

from marquise import (
    CinemaSourceAssignmentNotFoundError,
    MarquiseFactory,
)
from marquise_cli.helpers import run_spinner, run_with_factory, select_cinema


async def run_unassign(factory: MarquiseFactory) -> None:
    """Remove showtime-source assignment from a cinema."""
    selected = await select_cinema(
        factory, "Select a cinema to unassign a source from:"
    )
    if selected is None:
        return

    unassign_source_use_case = factory.sources.unassign_source_use_case
    response = await run_spinner(
        unassign_source_use_case.execute(
            unassign_source_use_case.InputData(cinema_id=selected.id)
        ),
        description="Removing source assignment...",
    )
    print(f"Source unassigned from cinema {response.cinema_id}.")


def unassign() -> None:
    """Remove showtime-source assignment from a cinema."""
    try:
        asyncio.run(run_with_factory(run_unassign))
    except CinemaSourceAssignmentNotFoundError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
