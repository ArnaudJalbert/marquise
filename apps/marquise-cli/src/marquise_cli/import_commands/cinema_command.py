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


def import_cinema() -> None:
    """Fetch showtimes from one cinema source and save them to database."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            selected = await select_cinema(
                factory, "Select a cinema to import showtimes for:"
            )
            if selected is None:
                return

            assignment = await factory.source.get_cinema_source(cinema_id=selected.id)
            print(f"  Cinema:        {selected.name}")
            print(f"  Assigned source: {assignment.source_display_name}")

            today = date.today()
            frame_choice = await questionary.select(
                "Date range (from today):",
                choices=[
                    questionary.Choice(
                        title="1 day  (today–tomorrow)", value=timedelta(days=1)
                    ),
                    questionary.Choice(
                        title="1 week  (7 days)", value=timedelta(weeks=1)
                    ),
                    questionary.Choice(
                        title="2 weeks  (14 days)", value=timedelta(weeks=2)
                    ),
                    questionary.Choice(
                        title="1 month  (30 days)", value=timedelta(days=30)
                    ),
                    questionary.Choice(title="Custom range…", value="__custom__"),
                ],
            ).ask_async()
            if frame_choice is None:
                print("Cancelled.")
                return

            if frame_choice == "__custom__":
                start_str = await questionary.text(
                    "Start date (YYYY-MM-DD):"
                ).ask_async()
                if start_str is None or not start_str.strip():
                    print("Cancelled.")
                    return

                end_str = await questionary.text("End date (YYYY-MM-DD):").ask_async()
                if end_str is None or not end_str.strip():
                    print("Cancelled.")
                    return

                try:
                    start_date = date.fromisoformat(start_str)
                    end_date = date.fromisoformat(end_str)
                except ValueError:
                    print("Invalid date format. Use YYYY-MM-DD.", file=sys.stderr)
                    raise SystemExit(1)
            else:
                start_date = today
                end_date = today + frame_choice

            result = await run_spinner(
                factory.source.import_screenings(
                    cinema_id=selected.id,
                    start_date=start_date,
                    end_date=end_date,
                ),
                description="Importing screenings...",
            )
            table = Table(
                title=(
                    f"Imported screenings for {result.cinema_name}"
                    f" ({result.source_name})"
                )
            )
            table.add_column("Movie", style="cyan")
            table.add_column("Showtime")
            table.add_column("Status")
            for screening in result.screenings:
                local_time = datetime.fromisoformat(screening.showtime).astimezone(
                    _MONTREAL_TZ
                )
                table.add_row(
                    screening.movie_title,
                    local_time.strftime("%Y-%m-%d %H:%M"),
                    "imported" if screening.imported else "updated",
                )
            _console.print(table)

            summary = Text(f"{result.total_count} total  |  ")
            summary.append(f"{result.imported_count}", style="green")
            summary.append(" new  |  ")
            summary.append(f"{result.updated_count}", style="yellow")
            summary.append(" updated")
            if result.skipped_count:
                summary.append("  |  ")
                summary.append(f"{result.skipped_count}", style="red")
                summary.append(" skipped")
            _console.print(summary)
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        raise SystemExit(1)
