"""Source management CLI commands."""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import questionary
from rich.console import Console
from rich.table import Table
from rich.text import Text

from marquise import ListCinemasUseCase, MarquiseFactory
from marquise_cli.helpers import run_spinner, select_source

_console = Console()
MONTREAL_TZ = ZoneInfo("America/Toronto")


def list_registered_sources() -> None:
    """List registered showtime sources in the database."""

    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            response = await run_spinner(
                factory.source.list_sources(),
                description="Fetching registered sources...",
            )
        finally:
            await factory.shutdown()

        if not response.sources:
            print("No sources registered.")
            return

        table = Table(title="Registered sources")
        table.add_column("Name", style="cyan")
        table.add_column("Display Name")
        table.add_column("Description")

        for s in response.sources:
            description = s.description or ""
            table.add_row(s.name, s.display_name, description)

        _console.print(table)

    try:
        asyncio.run(_run())
    except Exception as e:
        print(f"Failed to list sources: {e}", file=sys.stderr)
        raise SystemExit(1) from e


def assign() -> None:
    """Assign a showtime source to a cinema after interactive selection."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            selected = await _select_cinema(
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
    except Exception as e:
        print(f"Failed to assign source: {e}", file=sys.stderr)
        raise SystemExit(1) from e


def unassign() -> None:
    """Remove the showtime source assignment from a cinema."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            selected = await _select_cinema(
                factory, "Select a cinema to unassign a source from:"
            )
            if selected is None:
                return

            response = await run_spinner(
                factory.source.unassign_source(
                    cinema_id=selected.id,
                ),
                description="Removing source assignment...",
            )
            print(f"Source unassigned from cinema {response.cinema_id}.")
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Failed to unassign source: {e}", file=sys.stderr)
        raise SystemExit(1) from e


# ---------------------------------------------------------------------------
# source registry — list sources available in the code-level registry
# ---------------------------------------------------------------------------


def list_available_sources() -> None:
    """List showtime sources available in the code-level registry.

    Shows which sources are available and whether they are already
    registered in the database.  No database connection required for the
    registry list, but one is needed to check registration status.
    """
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            registry_response = await run_spinner(
                factory.source.list_registry_sources(),
                description="Fetching available sources...",
            )

            if not registry_response.sources:
                print("No sources registered in the registry.")
                return

            db_names: set[str] = set()
            try:
                db_response = await run_spinner(
                    factory.source.list_sources(),
                    description="Checking registrations...",
                )
                db_names = {s.name for s in db_response.sources}
            except Exception:
                pass

            table = Table(title="Available sources")
            table.add_column("Name", style="cyan")
            table.add_column("Registered")

            for entry in registry_response.sources:
                registered = "✓" if entry.name in db_names else "—"
                table.add_row(entry.name, registered)

            _console.print(table)
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except Exception as e:
        print(f"Failed to list registry sources: {e}", file=sys.stderr)
        raise SystemExit(1) from e


# ---------------------------------------------------------------------------
# source register — sync registry sources to the database
# ---------------------------------------------------------------------------


def register_sources() -> None:
    """Register new showtime sources from the registry into the database.

    Shows which sources are available in the code-level registry and
    which are already registered in the database.  For new sources,
    prompts for display name and description before saving.
    """
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            registry_response = await run_spinner(
                factory.source.list_registry_sources(),
                description="Fetching available sources...",
            )
            db_response = await run_spinner(
                factory.source.list_sources(),
                description="Fetching registered sources...",
            )

            db_names = {s.name for s in db_response.sources}
            new_sources = [
                s for s in registry_response.sources if s.name not in db_names
            ]

            if not registry_response.sources:
                print("No sources available in the registry.")
                return

            table = Table(title="Sources available in registry")
            table.add_column("Name", style="cyan")
            table.add_column("Status")

            for entry in registry_response.sources:
                if entry.name in db_names:
                    status = "already registered"
                else:
                    status = "new"
                table.add_row(entry.name, status)

            _console.print(table)

            if not new_sources:
                print("All registry sources are already in the database.")
                return

            print(f"{len(new_sources)} source(s) can be registered.")

            for entry in new_sources:
                print(f"\n--- Registering: {entry.name} ---")
                display_name = await questionary.text(
                    "Display name:",
                ).ask_async()
                if display_name is None:
                    print("Cancelled.")
                    return

                description = await questionary.text(
                    "Description (optional):",
                ).ask_async()
                if description is None:
                    print("Cancelled.")
                    return

                desc_val = description if description.strip() else None

                try:
                    result = await run_spinner(
                        factory.source.create_source(
                            name=entry.name,
                            display_name=display_name,
                            description=desc_val,
                        ),
                        description=f"Registering {entry.name}...",
                    )
                    print(f"  Created: {result.name}")
                except Exception as e:
                    print(
                        f"  Failed: {e}",
                        file=sys.stderr,
                    )

        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Failed to register sources: {e}", file=sys.stderr)
        raise SystemExit(1) from e


# ---------------------------------------------------------------------------
# source unregister — remove sources from the database
# ---------------------------------------------------------------------------


def unregister_sources() -> None:
    """Remove showtime sources from the database.

    Shows which sources are in the database and whether they correspond
    to a code-level source.  Lets you pick which ones to remove.
    """
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            registry_response = await run_spinner(
                factory.source.list_registry_sources(),
                description="Fetching available sources...",
            )
            db_response = await run_spinner(
                factory.source.list_sources(),
                description="Fetching registered sources...",
            )

            if not db_response.sources:
                print("No sources registered in the database.")
                return

            registry_names = {s.name for s in registry_response.sources}

            table = Table(title="Sources in database")
            table.add_column("Name", style="cyan")
            table.add_column("Status")

            for s in db_response.sources:
                if s.name in registry_names:
                    status = "in registry"
                else:
                    status = "not in registry"
                table.add_row(s.name, status)

            _console.print(table)

            selected = await questionary.checkbox(
                "Select sources to unregister:",
                choices=[
                    questionary.Choice(
                        title=f"{s.display_name} ({s.name})",
                        value=s.name,
                    )
                    for s in db_response.sources
                ],
            ).ask_async()

            if selected is None or not selected:
                print("No sources selected.")
                return

            confirmed = await questionary.confirm(
                f"Remove {len(selected)} source(s) from the database?",
                default=False,
            ).ask_async()

            if not confirmed:
                print("Cancelled.")
                return

            for source_name in selected:
                try:
                    await run_spinner(
                        factory.source.delete_source(
                            source_name=source_name,
                        ),
                        description=f"Removing {source_name}...",
                    )
                    print(f"  Removed: {source_name}")
                except Exception as e:
                    print(
                        f"  Failed: {e}",
                        file=sys.stderr,
                    )

        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Failed to unregister sources: {e}", file=sys.stderr)
        raise SystemExit(1) from e


# ---------------------------------------------------------------------------
# source import — fetch and save showtimes for a cinema
# ---------------------------------------------------------------------------


def import_screenings() -> None:
    """Fetch showtimes from a cinema's source and save them to the database.

    Selects a cinema interactively, prompts for a date range, then
    displays a summary of imported or already-existing screenings.
    """
    factory = MarquiseFactory()

    async def _run() -> None:
        await run_spinner(factory.initialize(), description="Connecting...")
        try:
            selected = await _select_cinema(
                factory, "Select a cinema to import showtimes for:"
            )
            if selected is None:
                return

            assignment = await factory.source.get_cinema_source(
                cinema_id=selected.id,
            )
            print(f"  Cinema:        {selected.name}")
            print(f"  Assigned source: {assignment.source_display_name}")

            today = date.today()
            frame_choice = await questionary.select(
                "Date range (from today):",
                choices=[
                    questionary.Choice(
                        title="1 day  (today–tomorrow)",
                        value=timedelta(days=1),
                    ),
                    questionary.Choice(
                        title="1 week  (7 days)",
                        value=timedelta(weeks=1),
                    ),
                    questionary.Choice(
                        title="2 weeks  (14 days)",
                        value=timedelta(weeks=2),
                    ),
                    questionary.Choice(
                        title="1 month  (30 days)",
                        value=timedelta(days=30),
                    ),
                    questionary.Choice(title="Custom range…", value="__custom__"),
                ],
            ).ask_async()
            if frame_choice is None:
                print("Cancelled.")
                return

            if frame_choice == "__custom__":
                start_str = await questionary.text(
                    "Start date (YYYY-MM-DD):",
                ).ask_async()
                if start_str is None or not start_str.strip():
                    print("Cancelled.")
                    return

                end_str = await questionary.text(
                    "End date (YYYY-MM-DD):",
                ).ask_async()
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

            for s in result.screenings:
                status = "imported" if s.imported else "updated"
                dt = datetime.fromisoformat(s.showtime).astimezone(MONTREAL_TZ)
                local_time = dt.strftime("%Y-%m-%d %H:%M")
                table.add_row(s.movie_title, local_time, status)

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


# ---------------------------------------------------------------------------
# Interactive selection helpers
# ---------------------------------------------------------------------------


async def _select_cinema(
    factory: MarquiseFactory,
    prompt: str,
) -> ListCinemasUseCase.CinemaData | None:
    """Let the user pick a cinema interactively from a list.

    Args:
        factory: The factory providing controllers.
        prompt: The question to display in the selector.

    Returns:
        The selected cinema data, or ``None`` if the user cancelled.
    """
    try:
        response = await factory.cinema.list_cinemas()
    except Exception:
        raise

    if not response.cinemas:
        print("No cinemas available.")
        return None

    choices = [
        questionary.Choice(
            title=f"{c.name} — {c.address or 'No address'}, {c.city or 'No city'}",
            value=c,
        )
        for c in response.cinemas
    ]
    choices.append(questionary.Choice(title="← exit", value="__exit__"))

    selected = await questionary.select(prompt, choices=choices).ask_async()

    if selected is None or selected == "__exit__":
        print("Cancelled.")
        return None

    return selected
