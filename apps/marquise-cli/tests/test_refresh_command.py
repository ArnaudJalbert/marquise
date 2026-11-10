"""Refresh delivery tests use only public DTOs and an autospecced executor."""

from unittest.mock import create_autospec

import pytest

from marquise import (
    ApplicationError,
    EnrichMovieOutputData,
    MetadataFailure,
    MetadataInvalidDataError,
    MetadataNotFoundError,
    MetadataRateLimitedError,
    MetadataUnavailableError,
    MovieNotFoundError,
    RefreshMoviesExecutor,
    RefreshMoviesInputData,
    RefreshMoviesOutputData,
)
from marquise_cli.refresh_command import run_refresh_movies


@pytest.mark.asyncio
@pytest.mark.parametrize("movie_id", ["movie-001", " opaque movie ID "])
async def test_refresh_one_preserves_id(
    movie_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """One target reaches the public executor unchanged and prints its stable ID."""
    executor = create_autospec(RefreshMoviesExecutor, instance=True, spec_set=True)
    output = RefreshMoviesOutputData((EnrichMovieOutputData(movie_id, "enriched"),))
    executor.execute.return_value = output

    assert await run_refresh_movies(executor, movie_id=movie_id) == 0

    executor.execute.assert_awaited_once_with(RefreshMoviesInputData(movie_id))
    captured = capsys.readouterr()
    assert captured.out == (
        f"[refreshed] {movie_id}\nDone: 1 refreshed, 0 skipped, 0 failed.\n"
    )
    assert captured.err == ""
    assert output.results[0].movie_id == movie_id


@pytest.mark.asyncio
async def test_refresh_all_reports_partial_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A failed middle record retains successful and unchanged records and totals."""
    executor = create_autospec(RefreshMoviesExecutor, instance=True, spec_set=True)
    executor.execute.return_value = RefreshMoviesOutputData(
        (
            EnrichMovieOutputData("movie-001", "enriched"),
            EnrichMovieOutputData(
                "movie-002",
                "failed",
                MetadataRateLimitedError("secret provider URL"),
            ),
            EnrichMovieOutputData("movie-003", "unchanged"),
            EnrichMovieOutputData("movie-004", "enriched"),
        )
    )

    assert await run_refresh_movies(executor, all_movies=True) == 1

    executor.execute.assert_awaited_once_with(RefreshMoviesInputData())
    captured = capsys.readouterr()
    assert captured.out == (
        "[refreshed] movie-001\n"
        "[skipped] movie-003: unchanged\n"
        "[refreshed] movie-004\n"
        "Done: 2 refreshed, 1 skipped, 1 failed.\n"
    )
    assert captured.err == "[failed] movie-002: MetadataRateLimitedError (retryable)\n"
    assert "secret" not in captured.out + captured.err


@pytest.mark.asyncio
async def test_refresh_all_empty(capsys: pytest.CaptureFixture[str]) -> None:
    """No confirmed movies is a successful empty bulk refresh."""
    executor = create_autospec(RefreshMoviesExecutor, instance=True, spec_set=True)
    executor.execute.return_value = RefreshMoviesOutputData(())

    assert await run_refresh_movies(executor, all_movies=True) == 0

    executor.execute.assert_awaited_once_with(RefreshMoviesInputData())
    assert capsys.readouterr().out == "Done: 0 refreshed, 0 skipped, 0 failed.\n"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("movie_id", "all_movies"),
    [(None, False), ("movie-001", True), ("", False), (" \t", False), ("", True)],
)
async def test_invalid_target_never_executes(
    movie_id: str | None, all_movies: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing, blank or contradictory targets fail before any application call."""
    executor = create_autospec(RefreshMoviesExecutor, instance=True, spec_set=True)

    assert (
        await run_refresh_movies(executor, movie_id=movie_id, all_movies=all_movies)
        == 2
    )

    executor.execute.assert_not_awaited()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Choose one movie ID or all movies.\n"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,printed",
    [
        (MetadataNotFoundError("Movie not found"), "MetadataNotFoundError"),
        (
            MetadataInvalidDataError("Movie has no confirmed TMDB identity"),
            "MetadataInvalidDataError",
        ),
        (
            MetadataUnavailableError("secret credentials"),
            "MetadataUnavailableError (retryable)",
        ),
    ],
)
async def test_single_target_failure(
    failure: MetadataFailure, printed: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unknown, unconfirmed and unavailable targets retain explicit typed failure."""
    executor = create_autospec(RefreshMoviesExecutor, instance=True, spec_set=True)
    executor.execute.return_value = RefreshMoviesOutputData(
        (EnrichMovieOutputData("movie-001", "failed", failure),)
    )

    assert await run_refresh_movies(executor, movie_id="movie-001") == 1

    executor.execute.assert_awaited_once_with(RefreshMoviesInputData("movie-001"))
    captured = capsys.readouterr()
    assert captured.err == f"[failed] movie-001: {printed}\n"
    assert captured.out == "Done: 0 refreshed, 0 skipped, 1 failed.\n"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "message"),
    [
        (MovieNotFoundError("secret"), "movie not found."),
        (
            ApplicationError("secret"),
            "application error. Check configuration and confirmed movie identity.",
        ),
    ],
)
async def test_application_failure_is_safe_and_nonzero(
    error: ApplicationError, message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Documented executor errors cannot report success or leak error credentials."""
    executor = create_autospec(RefreshMoviesExecutor, instance=True, spec_set=True)
    executor.execute.side_effect = error

    assert await run_refresh_movies(executor, movie_id="movie-001") == 1

    executor.execute.assert_awaited_once_with(RefreshMoviesInputData("movie-001"))
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"Refresh failed: {message}\n"
