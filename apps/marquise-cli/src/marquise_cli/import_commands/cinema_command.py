"""Interactively import showtimes for one cinema."""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import questionary
from rich.table import Table
from rich.text import Text

from marquise import (
    CinemaSourceAssignmentNotFoundError,
    ImportScreeningsCommand,
    MarquiseFactory,
)
from marquise_cli.helpers import connected_factory, console, run_spinner, select_cinema

_MONTREAL_TZ = ZoneInfo("America/Montreal")


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
) -> ImportScreeningsCommand.OutputData:
    """Import one cinema date range."""
    return await factory.screenings.import_screenings_command.execute(
        ImportScreeningsCommand.InputData(
            cinema_id=cinema_id,
            start_date=start_date,
            end_date=end_date,
        )
    )


def _screenings_table(result: ImportScreeningsCommand.OutputData) -> Table:
    """Build imported-screenings table."""
    table = Table(
        title=(f"Imported screenings for {result.cinema_name} ({result.source_name})")
    )
    table.add_column("Movie", style="cyan")
    table.add_column("Showtime")
    table.add_column("Status")
    for screening in result.screenings:
        local_time = datetime.fromisoformat(screening.showtime).astimezone(_MONTREAL_TZ)
        table.add_row(
            screening.movie_title,
            local_time.strftime("%Y-%m-%d %H:%M"),
            (
                "imported"
                if screening.imported
                else "rescheduled"
                if screening.rescheduled
                else "updated"
            ),
        )
    return table


def _summary(result: ImportScreeningsCommand.OutputData) -> Text:
    """Build imported-screenings summary."""
    summary = Text(f"{result.total_count} total  |  ")
    summary.append(f"{result.imported_count}", style="green")
    summary.append(" new  |  ")
    summary.append(f"{result.updated_count}", style="yellow")
    summary.append(" updated")
    if result.rescheduled_count:
        summary.append("  |  ")
        summary.append(f"{result.rescheduled_count}", style="yellow")
        summary.append(" rescheduled")
    if result.skipped_count:
        summary.append("  |  ")
        summary.append(f"{result.skipped_count}", style="red")
        summary.append(" skipped")
    return summary


async def run_import_cinema(factory: MarquiseFactory) -> None:
    """Fetch showtimes from one cinema source and save them to database."""
    cinema = await select_cinema(factory, "Select a cinema to import showtimes for:")
    if cinema is None:
        return
    get_source_query = factory.sources.get_cinema_source_query
    assignment = await get_source_query.execute(
        get_source_query.InputData(cinema_id=cinema.id)
    )
    print(f"  Cinema:        {cinema.name}")
    print(f"  Assigned source: {assignment.source_display_name}")
    date_range = await _select_date_range()
    if date_range is None:
        return
    result = await run_spinner(
        _import_screenings(factory, cinema.id, *date_range),
        description="Importing screenings...",
    )
    console.print(_screenings_table(result))
    console.print(_summary(result))


def import_cinema() -> None:
    """Fetch showtimes from one cinema source and save them to database."""

    async def run() -> None:
        async with connected_factory() as factory:
            await run_import_cinema(factory)

    try:
        asyncio.run(run())
    except CinemaSourceAssignmentNotFoundError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
