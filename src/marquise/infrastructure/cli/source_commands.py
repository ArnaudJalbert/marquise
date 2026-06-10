"""Source management CLI commands."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import questionary
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from marquise.application.exceptions import CinemaSourceAssignmentNotFoundError
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.infrastructure.cli.helpers import run_spinner
from marquise.infrastructure.di.container import Container

source_app = typer.Typer(
    no_args_is_help=True,
)

_console = Console()


@source_app.command(name="list-registered", rich_help_panel="Information")
def list_registered_sources() -> None:
    """List registered showtime sources in the database (admin only)."""

    container = Container()

    async def _run() -> None:
        await run_spinner(container.initialize(), description="Connecting...")
        try:
            response = await run_spinner(
                container.source_controller.list_sources(),
                description="Fetching registered sources...",
            )
        finally:
            await container.shutdown()

        if not response.sources:
            typer.echo("No sources registered.")
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
        import asyncio

        asyncio.run(_run())
    except Exception as e:
        typer.echo(f"Failed to list sources: {e}", err=True)
        raise typer.Exit(code=1) from e


@source_app.command(rich_help_panel="Management")
def assign() -> None:
    """Assign a showtime source to a cinema after interactive selection (admin only)."""
    container = Container()

    async def _run() -> None:
        await run_spinner(container.initialize(), description="Connecting...")
        try:
            selected = await _select_cinema_admin(
                container, "Select a cinema to assign a source to:"
            )
            if selected is None:
                return

            source_name = await _select_source(container, "Select a source to assign:")
            if source_name is None:
                return

            response = await run_spinner(
                container.source_controller.assign_source(
                    cinema_id=selected.id,
                    source_name=source_name,
                ),
                description="Assigning source...",
            )
            typer.echo("Source assigned:")
            typer.echo(f"  Cinema:      {response.cinema_id}")
            typer.echo(f"  Source:      {response.source_name}")
        finally:
            await container.shutdown()

    try:
        import asyncio

        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"Failed to assign source: {e}", err=True)
        raise typer.Exit(code=1) from e


@source_app.command(rich_help_panel="Management")
def unassign() -> None:
    """Remove the showtime source assignment from a cinema (admin only)."""
    container = Container()

    async def _run() -> None:
        await run_spinner(container.initialize(), description="Connecting...")
        try:
            selected = await _select_cinema_admin(
                container, "Select a cinema to unassign a source from:"
            )
            if selected is None:
                return

            response = await run_spinner(
                container.source_controller.unassign_source(
                    cinema_id=selected.id,
                ),
                description="Removing source assignment...",
            )
            typer.echo(f"Source unassigned from cinema {response.cinema_id}.")
        finally:
            await container.shutdown()

    try:
        import asyncio

        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"Failed to unassign source: {e}", err=True)
        raise typer.Exit(code=1) from e


@source_app.command(name="list-assignments", rich_help_panel="Information")
def list_assignments() -> None:
    """Display which showtime source is assigned to each cinema.

    This is a public operation — no authentication required.
    """
    container = Container()

    async def _run() -> None:
        await run_spinner(container.initialize(), description="Connecting...")
        try:
            cinemas_response = await run_spinner(
                container.cinema_controller.list(),
                description="Fetching cinemas...",
            )

            if not cinemas_response.cinemas:
                typer.echo("No cinemas found.")
                return

            table = Table(title="Cinema source assignments")
            table.add_column("Cinema", style="cyan")
            table.add_column("Source")
            table.add_column("Source Display Name")

            for cinema in cinemas_response.cinemas:
                try:
                    assignment = await container.source_controller.get_cinema_source(
                        cinema_id=cinema.id,
                    )
                    table.add_row(
                        cinema.name,
                        assignment.source_name,
                        assignment.source_display_name,
                    )
                except CinemaSourceAssignmentNotFoundError:
                    table.add_row(cinema.name, "—", "—")

            _console.print(table)
        finally:
            await container.shutdown()

    try:
        import asyncio

        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"Failed to list assignments: {e}", err=True)
        raise typer.Exit(code=1) from e


# ---------------------------------------------------------------------------
# source registry — list sources available in the code-level registry
# ---------------------------------------------------------------------------


@source_app.command(name="list-available", rich_help_panel="Information")
def list_available_sources() -> None:
    """List showtime sources available in the code-level registry.

    Shows which sources are available and whether they are already
    registered in the database.  No database connection required for the
    registry list, but authentication is needed to check registration
    status.
    """
    container = Container()

    async def _run() -> None:
        await run_spinner(container.initialize(), description="Connecting...")
        try:
            registry_response = await run_spinner(
                container.source_controller.list_registry_sources(),
                description="Fetching available sources...",
            )

            if not registry_response.sources:
                typer.echo("No sources registered in the registry.")
                return

            db_names: set[str] = set()
            try:
                db_response = await run_spinner(
                    container.source_controller.list_sources(),
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
            await container.shutdown()

    try:
        import asyncio

        asyncio.run(_run())
    except Exception as e:
        typer.echo(f"Failed to list registry sources: {e}", err=True)
        raise typer.Exit(code=1) from e


# ---------------------------------------------------------------------------
# source register — sync registry sources to the database
# ---------------------------------------------------------------------------


@source_app.command("register", rich_help_panel="Management")
def register_sources() -> None:
    """Register new showtime sources from the registry into the database (admin only).

    Shows which sources are available in the code-level registry and
    which are already registered in the database.  For new sources,
    prompts for display name and description before saving.
    """
    container = Container()

    async def _run() -> None:
        await run_spinner(container.initialize(), description="Connecting...")
        try:
            registry_response = await run_spinner(
                container.source_controller.list_registry_sources(),
                description="Fetching available sources...",
            )
            db_response = await run_spinner(
                container.source_controller.list_sources(),
                description="Fetching registered sources...",
            )

            db_names = {s.name for s in db_response.sources}
            new_sources = [
                s for s in registry_response.sources if s.name not in db_names
            ]

            if not registry_response.sources:
                typer.echo("No sources available in the registry.")
                return

            table = Table(title="Sources available in registry")
            table.add_column("Name", style="cyan")
            table.add_column("Status")

            for entry in registry_response.sources:
                if entry.name in db_names:
                    status = typer.style("already registered", fg=typer.colors.GREEN)
                else:
                    status = typer.style("new", fg=typer.colors.YELLOW)
                table.add_row(entry.name, status)

            _console.print(table)

            if not new_sources:
                typer.echo("All registry sources are already in the database.")
                return

            typer.echo(f"{len(new_sources)} source(s) can be registered.")

            for entry in new_sources:
                typer.echo(f"\n--- Registering: {entry.name} ---")
                display_name = await questionary.text(
                    "Display name:",
                ).ask_async()
                if display_name is None:
                    typer.echo("Cancelled.")
                    return

                description = await questionary.text(
                    "Description (optional):",
                ).ask_async()
                if description is None:
                    typer.echo("Cancelled.")
                    return

                desc_val = description if description.strip() else None

                try:
                    result = await run_spinner(
                        container.source_controller.create_source(
                            name=entry.name,
                            display_name=display_name,
                            description=desc_val,
                        ),
                        description=f"Registering {entry.name}...",
                    )
                    typer.echo(
                        typer.style(
                            f"  Created: {result.name}",
                            fg=typer.colors.GREEN,
                        )
                    )
                except Exception as e:
                    typer.echo(
                        typer.style(f"  Failed: {e}", fg=typer.colors.RED),
                        err=True,
                    )

        finally:
            await container.shutdown()

    try:
        import asyncio

        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"Failed to register sources: {e}", err=True)
        raise typer.Exit(code=1) from e


# ---------------------------------------------------------------------------
# source unregister — remove sources from the database
# ---------------------------------------------------------------------------


@source_app.command("unregister", rich_help_panel="Management")
def unregister_sources() -> None:
    """Remove showtime sources from the database (admin only).

    Shows which sources are in the database and whether they correspond
    to a code-level source.  Lets you pick which ones to remove.
    """
    container = Container()

    async def _run() -> None:
        await run_spinner(container.initialize(), description="Connecting...")
        try:
            registry_response = await run_spinner(
                container.source_controller.list_registry_sources(),
                description="Fetching available sources...",
            )
            db_response = await run_spinner(
                container.source_controller.list_sources(),
                description="Fetching registered sources...",
            )

            if not db_response.sources:
                typer.echo("No sources registered in the database.")
                return

            registry_names = {s.name for s in registry_response.sources}

            table = Table(title="Sources in database")
            table.add_column("Name", style="cyan")
            table.add_column("Status")

            for s in db_response.sources:
                if s.name in registry_names:
                    status = typer.style("in registry", fg=typer.colors.GREEN)
                else:
                    status = typer.style("not in registry", fg=typer.colors.YELLOW)
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
                typer.echo("No sources selected.")
                return

            confirmed = await questionary.confirm(
                f"Remove {len(selected)} source(s) from the database?",
                default=False,
            ).ask_async()

            if not confirmed:
                typer.echo("Cancelled.")
                return

            for source_name in selected:
                try:
                    await run_spinner(
                        container.source_controller.delete_source(
                            source_name=source_name,
                        ),
                        description=f"Removing {source_name}...",
                    )
                    typer.echo(
                        typer.style(
                            f"  Removed: {source_name}",
                            fg=typer.colors.GREEN,
                        )
                    )
                except Exception as e:
                    typer.echo(
                        typer.style(f"  Failed: {e}", fg=typer.colors.RED),
                        err=True,
                    )

        finally:
            await container.shutdown()

    try:
        import asyncio

        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"Failed to unregister sources: {e}", err=True)
        raise typer.Exit(code=1) from e


# ---------------------------------------------------------------------------
# source import — fetch and save showtimes for a cinema
# ---------------------------------------------------------------------------


@source_app.command("import", rich_help_panel="Management")
def import_screenings() -> None:
    """Fetch showtimes from a cinema's source and save them to the database.

    Selects a cinema interactively, prompts for a date range, then
    displays a summary of imported or already-existing screenings.
    """
    container = Container()

    async def _run() -> None:
        await run_spinner(container.initialize(), description="Connecting...")
        try:
            selected = await _select_cinema_admin(
                container, "Select a cinema to import showtimes for:"
            )
            if selected is None:
                return

            assignment = await container.source_controller.get_cinema_source(
                cinema_id=selected.id,
            )
            typer.echo(f"  Cinema:        {selected.name}")
            typer.echo(f"  Assigned source: {assignment.source_display_name}")

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
                typer.echo("Cancelled.")
                return

            if frame_choice == "__custom__":
                start_str = await questionary.text(
                    "Start date (YYYY-MM-DD):",
                ).ask_async()
                if start_str is None or not start_str.strip():
                    typer.echo("Cancelled.")
                    return

                end_str = await questionary.text(
                    "End date (YYYY-MM-DD):",
                ).ask_async()
                if end_str is None or not end_str.strip():
                    typer.echo("Cancelled.")
                    return

                try:
                    start_date = date.fromisoformat(start_str)
                    end_date = date.fromisoformat(end_str)
                except ValueError:
                    typer.echo("Invalid date format. Use YYYY-MM-DD.", err=True)
                    raise typer.Exit(code=1)
            else:
                start_date = today
                end_date = today + frame_choice

            result = await run_spinner(
                container.source_controller.import_screenings(
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
                status = (
                    typer.style("imported", fg=typer.colors.GREEN)
                    if s.imported
                    else typer.style("already exists", fg=typer.colors.YELLOW)
                )
                table.add_row(s.movie_title, s.showtime, status)

            _console.print(table)
            summary = Text(f"{result.total_count} total  |  ")
            summary.append(f"{result.imported_count}", style="green")
            summary.append(" new  |  ")
            summary.append(f"{result.updated_count}", style="yellow")
            summary.append(" already existed")
            _console.print(summary)
        finally:
            await container.shutdown()

    try:
        import asyncio

        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Interactive selection helpers
# ---------------------------------------------------------------------------


async def _select_cinema_admin(
    container: Container,
    prompt: str,
) -> Optional[ListCinemasUseCase.CinemaData]:
    """Let the admin pick a cinema interactively from a list.

    Args:
        container: The DI container.
        prompt: The question to display in the selector.

    Returns:
        The selected cinema data, or ``None`` if the user cancelled.
    """
    try:
        response = await container.cinema_controller.list_cinemas()
    except Exception:
        raise

    if not response.cinemas:
        typer.echo("No cinemas available.")
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
        typer.echo("Cancelled.")
        return None

    return selected


async def _select_cinema_public(
    container: Container,
    prompt: str,
) -> Optional[ListCinemasUseCase.CinemaData]:
    """Let a user pick a cinema interactively (no auth required).

    Args:
        container: The DI container.
        prompt: The question to display in the selector.

    Returns:
        The selected cinema data, or ``None`` if the user cancelled.
    """
    try:
        response = await container.cinema_controller.list()
    except Exception:
        raise

    if not response.cinemas:
        typer.echo("No cinemas available.")
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
        typer.echo("Cancelled.")
        return None

    return selected


async def _select_source(
    container: Container,
    prompt: str,
) -> Optional[str]:
    """Let the admin pick a source interactively from a list.

    Args:
        container: The DI container.
        prompt: The question to display in the selector.

    Returns:
        The selected source name, or ``None`` if the user cancelled.
    """
    try:
        response = await container.source_controller.list_sources()
    except Exception:
        raise

    if not response.sources:
        typer.echo("No sources available.")
        return None

    choices = [
        questionary.Choice(
            title=f"{s.display_name} ({s.name})",
            value=s.name,
        )
        for s in response.sources
    ]
    choices.append(questionary.Choice(title="← exit", value="__exit__"))

    selected = await questionary.select(prompt, choices=choices).ask_async()

    if selected is None or selected == "__exit__":
        typer.echo("Cancelled.")
        return None

    return selected
