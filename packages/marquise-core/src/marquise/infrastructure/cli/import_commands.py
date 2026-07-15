"""Bulk / scheduled import CLI commands.

Provides ``marquise import all`` — import showtimes for every cinema that
has a source assignment, over a rolling date window.  Designed to be run
unattended (e.g. from a nightly CI cron job), so cinemas without a source
assignment are skipped rather than treated as errors.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, timedelta

import typer

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
)
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.infrastructure.di.container import Container

import_app = typer.Typer(no_args_is_help=True)


@dataclass(frozen=True, slots=True)
class CinemaImportResult:
    """Outcome of importing a single cinema during a bulk run.

    Attributes:
        cinema_name: The display name of the cinema.
        status: One of ``"imported"``, ``"skipped"``, or ``"failed"``.
        imported_count: Number of new screenings created (0 unless imported).
        updated_count: Number of existing screenings updated (0 unless imported).
        skipped_screenings_count: Number of individual screenings skipped
            due to an external_id collision (0 unless imported).
        detail: Optional human-readable detail (e.g. an error or skip reason).
    """

    cinema_name: str
    status: str
    imported_count: int = 0
    updated_count: int = 0
    skipped_screenings_count: int = 0
    detail: str | None = None


async def run_import_all(container: Container, days: int) -> list[CinemaImportResult]:
    """Import showtimes for every cinema with a source assignment.

    Cinemas without an assigned source are skipped (not errors). Per-cinema
    failures are captured as ``"failed"`` results so one bad cinema does not
    abort the whole run.

    Args:
        container: The initialized DI container.
        days: Size of the rolling import window in days (today inclusive).

    Returns:
        One ``CinemaImportResult`` per cinema processed.
    """
    today = date.today()
    end_date = today + timedelta(days=days - 1)

    cinemas_response = await container.cinema_controller.list()

    async def _import_cinema(
        cinema: ListCinemasUseCase.CinemaData,
    ) -> CinemaImportResult:
        typer.echo(f"  Importing {cinema.name}...")
        try:
            output = await container.source_controller.import_screenings(
                cinema_id=cinema.id,
                start_date=today,
                end_date=end_date,
            )
        except CinemaSourceAssignmentNotFoundError:
            return CinemaImportResult(
                cinema_name=cinema.name,
                status="skipped",
                detail="no source assigned",
            )
        except CinemaNotFoundError as exc:
            return CinemaImportResult(
                cinema_name=cinema.name,
                status="failed",
                detail=str(exc),
            )
        except Exception as exc:
            return CinemaImportResult(
                cinema_name=cinema.name,
                status="failed",
                detail=f"{type(exc).__name__}: {exc}",
            )
        else:
            return CinemaImportResult(
                cinema_name=cinema.name,
                status="imported",
                imported_count=output.imported_count,
                updated_count=output.updated_count,
                skipped_screenings_count=output.skipped_count,
            )

    return list(
        await asyncio.gather(*[_import_cinema(c) for c in cinemas_response.cinemas])
    )


@import_app.command(name="all")
def import_all(
    days: int = typer.Option(
        7,
        "--days",
        "-d",
        min=1,
        help="Number of days to import, starting today (inclusive).",
    ),
) -> None:
    """Import showtimes for every cinema that has a source assignment."""
    container = Container()
    today = date.today()
    end_date = today + timedelta(days=days - 1)
    typer.echo(f"Starting bulk import: {today} → {end_date} ({days} days)")

    async def _run() -> list[CinemaImportResult]:
        await container.initialize()
        try:
            return await run_import_all(container, days)
        finally:
            await container.shutdown()

    try:
        results = asyncio.run(_run())
    except Exception as e:
        typer.echo(
            f"Bulk import failed during initialization: {type(e).__name__}: {e}",
            err=True,
        )
        raise typer.Exit(code=1) from e

    imported = [r for r in results if r.status == "imported"]
    skipped = [r for r in results if r.status == "skipped"]
    failed = [r for r in results if r.status == "failed"]

    typer.echo("\nResults:")
    for r in imported:
        suffix = (
            f", {r.skipped_screenings_count} skipped"
            if r.skipped_screenings_count
            else ""
        )
        typer.echo(
            f"  [ok]      {r.cinema_name}: "
            f"{r.imported_count} new, {r.updated_count} updated{suffix}"
        )
    for r in skipped:
        typer.echo(f"  [skipped] {r.cinema_name}: {r.detail}")
    for r in failed:
        typer.echo(f"  [failed]  {r.cinema_name}: {r.detail}", err=True)

    total_new = sum(r.imported_count for r in imported)
    total_updated = sum(r.updated_count for r in imported)
    typer.echo(
        f"Done: {len(imported)} imported, {len(skipped)} skipped, "
        f"{len(failed)} failed — {total_new} new, {total_updated} updated."
    )

    if failed:
        raise typer.Exit(code=1)
