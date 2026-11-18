"""Assign a showtime source to a cinema."""

from __future__ import annotations

import asyncio
import sys

from marquise import (
    CinemaNotFoundError,
    CinemaSourceAssignmentAlreadyExistsError,
    MarquiseFactory,
    SourceNotFoundError,
)
from marquise_cli.helpers import (
    run_spinner,
    run_with_factory,
    select_cinema,
    select_source,
)


async def run_assign(factory: MarquiseFactory) -> None:
    """Assign a showtime source to a cinema after interactive selection."""
    selected = await select_cinema(factory, "Select a cinema to assign a source to:")
    if selected is None:
        return

    source_name = await select_source(factory, "Select a source to assign:")
    if source_name is None:
        return

    assign_source_use_case = factory.sources.assign_source_use_case
    response = await run_spinner(
        assign_source_use_case.execute(
            assign_source_use_case.InputData(
                cinema_id=selected.id,
                source_name=source_name,
            )
        ),
        description="Assigning source...",
    )
    print("Source assigned:")
    print(f"  Cinema:      {response.cinema_id}")
    print(f"  Source:      {response.source_name}")


def assign() -> None:
    """Assign a showtime source to a cinema after interactive selection."""
    try:
        asyncio.run(run_with_factory(run_assign))
    except (
        CinemaNotFoundError,
        SourceNotFoundError,
        CinemaSourceAssignmentAlreadyExistsError,
    ) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
