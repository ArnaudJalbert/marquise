"""Cinema listing CLI command."""

from __future__ import annotations

import asyncio

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from marquise import (
    ListCinemaSourceAssignmentsUseCase,
    MarquiseFactory,
)
from marquise_cli.helpers import run_spinner

_console = Console()


def list_cinemas(
    name: str | None = None,
    verbose: bool = False,
) -> None:
    """List all available cinemas."""

    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            response = await run_spinner(
                factory.cinema.list(name=name), description="Fetching cinemas..."
            )
            cinemas = response.cinemas

            if not cinemas:
                print("No cinemas found.")
                return

            source_names: dict[str, str] = {}
            if verbose:
                assignments = await run_spinner(
                    factory.list_cinema_source_assignments_use_case.execute(
                        ListCinemaSourceAssignmentsUseCase.InputData()
                    ),
                    description="Fetching source assignments...",
                )
                source_names = {
                    assignment.cinema_id: assignment.source_display_name
                    for assignment in assignments.assignments
                }

            table = Table(
                title="Available cinemas",
                box=box.ROUNDED,
                header_style="bold",
                show_lines=True,
            )
            table.add_column("Cinema", style="cyan", no_wrap=True)
            table.add_column("City", style="magenta")
            if verbose:
                table.add_column("Address", style="green", overflow="fold")
                table.add_column("Website", style="blue underline", overflow="fold")
                table.add_column("Source", style="yellow", overflow="fold")
                table.add_column("ID", style="dim")

            for cinema in cinemas:
                row: list[str | Text] = [cinema.name, cinema.city or "-"]
                if verbose:
                    website = Text("Website", style="blue underline")
                    if cinema.website:
                        website.stylize(f"link {cinema.website}")
                    row.extend(
                        [
                            cinema.address or "-",
                            website if cinema.website else "-",
                            source_names.get(cinema.id, ""),
                            cinema.id,
                        ]
                    )
                table.add_row(*row)

            _console.print(table)
        finally:
            await factory.shutdown()

    asyncio.run(_run())
