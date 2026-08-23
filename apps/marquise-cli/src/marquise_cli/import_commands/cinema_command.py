"""Interactively import showtimes for one cinema."""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import questionary
from rich.console import Console
from rich.table import Table
from rich.text import Text

from marquise import MarquiseFactory
from marquise_cli.helpers import run_spinner, select_cinema

_console = Console()
_MONTREAL_TZ = ZoneInfo("America/Toronto")


async def _select_date_range() -> tuple[date, date] | None:
    """Prompt for an import date range."""
    today = date.today()
    frame_choice = await questionary.select(
        "Date range (from today):",
        choices=[
            questionary.Choice("1 day  (today–tomorrow)", timedelta(days=1)),
            questionary.Choice("1 week  (7 days)", timedelta(weeks=1)),
            questionary.Choice("2 weeks  (14 days)", timedelta(weeks=2)),
            questionary.Choice("1 month  (30 days)", timedelta(days=30)),
            questionary.Choice("Custom range…", "__custom__"),
        ],
    ).ask_async()
    if frame_choice is None:
        print("Cancelled.")
        return None
    if frame_choice != "__custom__":
        return today, today + frame_choice

    start = await questionary.text("Start date (YYYY-MM-DD):").ask_async()
    if start is None or not start.strip():
        print("Cancelled.")
        return None
    end = await questionary.text("End date (YYYY-MM-DD):").ask_async()
    if end is None or not end.strip():
        print("Cancelled.")
        return None
    try:
        return date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD.", file=sys.stderr)
        raise SystemExit(1)


async def _import_screenings(
    factory: MarquiseFactory, cinema_id: str, start_date: date, end_date: date
) -> object:
    """Import one cinema date range."""
    return await run_spinner(
        factory.source.import_screenings(
            cinema_id=cinema_id, start_date=start_date, end_date=end_date
        ),
        description="Importing screenings...",
    )


def _screenings_table(result: object) -> Table:
    """Build imported-screenings table."""
    table = Table(
        title=f"Imported screenings for {result.cinema_name} ({result.source_name})"
    )  # type: ignore[attr-defined]
    table.add_column("Movie", style="cyan")
    table.add_column("Showtime")
    table.add_column("Status")
    for screening in result.screenings:  # type: ignore[attr-defined]
        local_time = datetime.fromisoformat(screening.showtime).astimezone(_MONTREAL_TZ)
        table.add_row(
            screening.movie_title,
            local_time.strftime("%Y-%m-%d %H:%M"),
            "imported" if screening.imported else "updated",
        )
    return table


def _summary(result: object) -> Text:
    """Build imported-screenings summary."""
    summary = Text(f"{result.total_count} total  |  ")  # type: ignore[attr-defined]
    summary.append(f"{result.imported_count}", style="green")  # type: ignore[attr-defined]
    summary.append(" new  |  ")
    summary.append(f"{result.updated_count}", style="yellow")  # type: ignore[attr-defined]
    summary.append(" updated")
    if result.skipped_count:  # type: ignore[attr-defined]
        summary.append("  |  ")
        summary.append(f"{result.skipped_count}", style="red")
        summary.append(" skipped")
    return summary


def import_cinema() -> None:
    """Fetch showtimes from one cinema source and save them to database."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            cinema = await select_cinema(
                factory, "Select a cinema to import showtimes for:"
            )
            if cinema is None:
                return
            assignment = await factory.source.get_cinema_source(cinema_id=cinema.id)
            print(f"  Cinema:        {cinema.name}")
            print(f"  Assigned source: {assignment.source_display_name}")
            date_range = await _select_date_range()
            if date_range is None:
                return
            result = await _import_screenings(factory, cinema.id, *date_range)
            _console.print(_screenings_table(result))
            _console.print(_summary(result))
        finally:
            await factory.shutdown()

    asyncio.run(_run())
