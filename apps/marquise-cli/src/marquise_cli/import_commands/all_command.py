"""Bulk / scheduled import CLI commands.

Provides ``marquise import all`` — import showtimes for every cinema that
has a source assignment, over a rolling date window.  Designed to be run
unattended (e.g. from a nightly CI cron job), so cinemas without a source
assignment are skipped rather than treated as errors.
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, timedelta

from marquise import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
    ImportScreeningsCommand,
    ListCinemasUseCase,
    MarquiseFactory,
)
from marquise_cli.helpers import connected_factory, list_every_cinema


@dataclass(frozen=True, slots=True)
class CinemaImportResult:
    """Outcome of importing a single cinema during a bulk run.

    Attributes:
        cinema_name: The display name of the cinema.
        status: One of ``"imported"``, ``"skipped"``, or ``"failed"``.
        imported_count: Number of new screenings created (0 unless imported).
        updated_count: Number of existing screenings updated (0 unless imported).
        rescheduled_count: Number of existing screenings moved in place.
        skipped_screenings_count: Number of individual screenings skipped
            due to an external_id collision (0 unless imported).
        detail: Optional human-readable detail (e.g. an error or skip reason).
        skipped_movies: Movies imported without an identity for bad TMDB data
            or an uncertain match.
        unmatched_movies: Movies with no matching TMDB record.
    """

    cinema_name: str
    status: str
    imported_count: int = 0
    updated_count: int = 0
    rescheduled_count: int = 0
    skipped_screenings_count: int = 0
    detail: str | None = None
    skipped_movies: tuple[ImportScreeningsCommand.UnresolvedMovieData, ...] = ()
    unmatched_movies: tuple[ImportScreeningsCommand.UnresolvedMovieData, ...] = ()


async def _run_bounded_cinema_import(
    import_cinema: Callable[
        [ListCinemasUseCase.CinemaData], Awaitable[CinemaImportResult]
    ],
    cinema: ListCinemasUseCase.CinemaData,
    semaphore: asyncio.Semaphore,
) -> CinemaImportResult:
    """Run one cinema import while respecting the bulk concurrency limit."""
    async with semaphore:
        return await import_cinema(cinema)


async def run_import_all(
    factory: MarquiseFactory, days: int
) -> list[CinemaImportResult]:
    """Import showtimes for every cinema with a source assignment.

    Cinemas without an assigned source are skipped (not errors). Per-cinema
    failures are captured as ``"failed"`` results so one bad cinema does not
    abort the whole run.

    Args:
        factory: The factory providing controllers.
        days: Size of the rolling import window in days (today inclusive).

    Returns:
        One ``CinemaImportResult`` per cinema processed.
    """
    today = date.today()
    end_date = today + timedelta(days=days - 1)
    print(f"Starting bulk import: {today} → {end_date} ({days} days)")

    cinemas = await list_every_cinema(factory, name=None)

    async def _import_cinema(
        cinema: ListCinemasUseCase.CinemaData,
    ) -> CinemaImportResult:
        print(f"  Importing {cinema.name}...")
        try:
            output = await factory.screenings.import_screenings_command.execute(
                ImportScreeningsCommand.InputData(
                    cinema_id=cinema.id,
                    start_date=today,
                    end_date=end_date,
                )
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
                rescheduled_count=output.rescheduled_count,
                skipped_screenings_count=output.skipped_count,
                skipped_movies=output.skipped_movies,
                unmatched_movies=output.unmatched_movies,
            )

    semaphore = asyncio.Semaphore(2)
    return list(
        await asyncio.gather(
            *(
                _run_bounded_cinema_import(_import_cinema, cinema, semaphore)
                for cinema in cinemas
            )
        )
    )


def _print_totals(
    imported: list[CinemaImportResult],
    skipped: list[CinemaImportResult],
    failed: list[CinemaImportResult],
) -> None:
    """Print aggregate bulk-import counts."""
    total_new = sum(result.imported_count for result in imported)
    total_updated = sum(result.updated_count for result in imported)
    total_rescheduled = sum(result.rescheduled_count for result in imported)
    print(
        f"Done: {len(imported)} imported, {len(skipped)} skipped, "
        f"{len(failed)} failed - {total_new} new, {total_updated} updated, "
        f"{total_rescheduled} rescheduled."
    )


def _print_movie_report(heading: str, results: list[CinemaImportResult]) -> None:
    """Print counts by reason, then each skipped and unmatched movie."""
    sections = {
        "Skipped": [
            (result.cinema_name, movie)
            for result in results
            for movie in result.skipped_movies
        ],
        "Unmatched": [
            (result.cinema_name, movie)
            for result in results
            for movie in result.unmatched_movies
        ],
    }
    counts = Counter(
        movie.reason for movies in sections.values() for _, movie in movies
    )
    if not counts:
        print(f"\nMovies for {heading}: none skipped or unmatched")
        return
    totals = ", ".join(f"{reason} {count}" for reason, count in sorted(counts.items()))
    print(f"\nMovies for {heading}: {totals}")
    for label, movies in sections.items():
        if movies:
            print(f"  {label}:")
        for cinema_name, movie in movies:
            print(f"    {cinema_name} | {movie.title} | {movie.reason}")


def _print_results(results: list[CinemaImportResult]) -> int:
    """Print bulk-import results and return failure count."""
    imported = [result for result in results if result.status == "imported"]
    skipped = [result for result in results if result.status == "skipped"]
    failed = [result for result in results if result.status == "failed"]

    print("\nResults:")
    for result in imported:
        suffix = (
            f", {result.rescheduled_count} rescheduled"
            if result.rescheduled_count
            else ""
        )
        suffix += (
            f", {result.skipped_screenings_count} skipped"
            if result.skipped_screenings_count
            else ""
        )
        print(
            f"  [ok]      {result.cinema_name}: "
            f"{result.imported_count} new, {result.updated_count} updated{suffix}"
        )
    for result in skipped:
        print(f"  [skipped] {result.cinema_name}: {result.detail}")
    for result in failed:
        print(f"  [failed]  {result.cinema_name}: {result.detail}", file=sys.stderr)

    for result in imported:
        if result.skipped_movies or result.unmatched_movies:
            _print_movie_report(result.cinema_name, [result])
    _print_movie_report("the run", imported)
    _print_totals(imported, skipped, failed)
    return len(failed)


def import_all(days: int) -> None:
    """Import showtimes for every cinema that has a source assignment."""

    async def run() -> list[CinemaImportResult]:
        async with connected_factory() as factory:
            return await run_import_all(factory, days)

    results = asyncio.run(run())

    if _print_results(results):
        raise SystemExit(1)
