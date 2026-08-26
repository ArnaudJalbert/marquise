"""Bulk / scheduled import CLI commands.

Provides ``marquise import all`` — import showtimes for every cinema that
has a source assignment, over a rolling date window.  Designed to be run
unattended (e.g. from a nightly CI cron job), so cinemas without a source
assignment are skipped rather than treated as errors.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import date, timedelta

from marquise import (
    CinemaNotFoundError,
    CinemaSourceAssignmentNotFoundError,
    ListCinemasUseCase,
    MarquiseFactory,
)


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
    await factory.initialize()
    try:
        today = date.today()
        end_date = today + timedelta(days=days - 1)

        list_cinemas_use_case = factory.list_cinemas_use_case
        cinemas_response = await list_cinemas_use_case.execute(
            list_cinemas_use_case.InputData()
        )

        async def _import_cinema(
            cinema: ListCinemasUseCase.CinemaData,
        ) -> CinemaImportResult:
            print(f"  Importing {cinema.name}...")
            try:
                fetch_use_case = factory.fetch_screenings_use_case
                fetched = await fetch_use_case.execute(
                    fetch_use_case.InputData(
                        cinema_id=cinema.id,
                        start_date=today,
                        end_date=end_date,
                    )
                )
                movies_use_case = factory.create_movies_use_case
                movies = await movies_use_case.execute(
                    movies_use_case.InputData(
                        movies=tuple(
                            movies_use_case.MovieInput(
                                title=movie.title,
                                description=movie.description,
                                directors=movie.directors,
                                cast=movie.cast,
                                duration_minutes=movie.duration_minutes,
                                release_year=movie.release_year,
                                poster_url=movie.poster_url,
                                trailer_url=movie.trailer_url,
                                genres=movie.genres,
                                original_title=movie.original_title,
                                rating=movie.rating,
                                origin_countries=movie.origin_countries,
                            )
                            for movie in fetched.movies
                        )
                    )
                )
                title_to_id = {movie.title: movie.id for movie in movies.movies}
                screenings_use_case = factory.create_screenings_use_case
                output = await screenings_use_case.execute(
                    screenings_use_case.InputData(
                        screenings=tuple(
                            screenings_use_case.ScreeningInput(
                                movie_id=title_to_id[
                                    _normalize_title(screening.movie_title)
                                ],
                                movie_title=screening.movie_title,
                                cinema_id=fetched.cinema_id,
                                cinema_name=fetched.cinema_name,
                                showtime=screening.showtime,
                                external_id=screening.external_id,
                                ticket_url=screening.ticket_url,
                                room=screening.room,
                                language=screening.language,
                            )
                            for screening in fetched.screenings
                        )
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
                    skipped_screenings_count=output.skipped_count,
                )

        return list(
            await asyncio.gather(*[_import_cinema(c) for c in cinemas_response.cinemas])
        )
    finally:
        await factory.shutdown()


def _normalize_title(title: str) -> str:
    """Strip and collapse internal whitespace in a scraped movie title."""
    return " ".join(title.strip().split())


def _print_totals(
    imported: list[CinemaImportResult],
    skipped: list[CinemaImportResult],
    failed: list[CinemaImportResult],
) -> None:
    """Print aggregate bulk-import counts."""
    total_new = sum(result.imported_count for result in imported)
    total_updated = sum(result.updated_count for result in imported)
    print(
        f"Done: {len(imported)} imported, {len(skipped)} skipped, "
        f"{len(failed)} failed — {total_new} new, {total_updated} updated."
    )


def _print_results(results: list[CinemaImportResult]) -> int:
    """Print bulk-import results and return failure count."""
    imported = [result for result in results if result.status == "imported"]
    skipped = [result for result in results if result.status == "skipped"]
    failed = [result for result in results if result.status == "failed"]

    print("\nResults:")
    for result in imported:
        suffix = (
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

    _print_totals(imported, skipped, failed)
    return len(failed)


def import_all(days: int) -> None:
    """Import showtimes for every cinema that has a source assignment."""
    today = date.today()
    end_date = today + timedelta(days=days - 1)
    print(f"Starting bulk import: {today} → {end_date} ({days} days)")

    results = asyncio.run(run_import_all(MarquiseFactory(), days))

    if _print_results(results):
        raise SystemExit(1)
