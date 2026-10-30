"""Metadata refresh delivery, injected and registered by issue #355."""

import sys

from marquise import (
    ApplicationError,
    MovieNotFoundError,
    RefreshMoviesExecutor,
    RefreshMoviesInputData,
    RefreshMoviesOutputData,
)


def _print_results(output: RefreshMoviesOutputData) -> int:
    """Show every stable movie ID and return a command exit status."""
    refreshed = skipped = failed = 0
    for result in output.results:
        if result.status == "enriched":
            print(f"[refreshed] {result.movie_id}")
            refreshed += 1
        elif result.status == "unchanged":
            print(f"[skipped] {result.movie_id}: unchanged")
            skipped += 1
        else:
            failed += 1
            failure = result.failure
            assert failure is not None  # Enforced by the public result DTO.
            # Provider messages may include request URLs or credentials.
            print(
                f"[failed] {result.movie_id}: {failure.kind}"
                + (" (retryable)" if failure.retryable else ""),
                file=sys.stderr,
            )
    print(f"Done: {refreshed} refreshed, {skipped} skipped, {failed} failed.")
    return 1 if failed else 0


async def run_refresh_movies(
    executor: RefreshMoviesExecutor,
    *,
    movie_id: str | None = None,
    all_movies: bool = False,
) -> int:
    """Refresh exactly one target or all confirmed movies through public DTOs.

    Return 0 on success, 1 for execution/per-record failures, or 2 for invalid
    input. IDs are opaque strings and pass through unchanged. The executor owns
    eligibility, enrichment policy, ordering and per-record failure isolation.
    Factory lifecycle, authentication/configuration and routing belong to #355.
    """
    if (movie_id is None and not all_movies) or (
        movie_id is not None and (all_movies or not movie_id.strip())
    ):
        print("Choose one movie ID or all movies.", file=sys.stderr)
        return 2
    try:
        output = await executor.execute(RefreshMoviesInputData(movie_id=movie_id))
    except MovieNotFoundError:
        print("Refresh failed: movie not found.", file=sys.stderr)
        return 1
    except ApplicationError:
        print(
            "Refresh failed: application error. Check configuration and "
            "confirmed movie identity.",
            file=sys.stderr,
        )
        return 1
    return _print_results(output)
