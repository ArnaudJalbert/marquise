"""Tests for the import workflow's response DTOs and InputData validators."""

from __future__ import annotations

from datetime import date

import pytest

from marquise.application.use_cases.fetch_showtimes_from_source import (
    FetchShowtimesFromSourceQuery,
)
from marquise.application.use_cases.import_screenings import (
    ImportedScreeningData,
    ImportScreeningsSummary,
)


def test_input_data_rejects_empty_cinema_id() -> None:
    """Verify FetchShowtimesFromSourceQuery.InputData rejects empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        FetchShowtimesFromSourceQuery.InputData(
            cinema_id="",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )


def test_input_data_rejects_whitespace_cinema_id() -> None:
    """Verify FetchShowtimesFromSourceQuery.InputData rejects whitespace cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        FetchShowtimesFromSourceQuery.InputData(
            cinema_id="   ",
            start_date=date(2026, 6, 7),
            end_date=date(2026, 6, 7),
        )


def test_input_data_rejects_start_date_after_end_date() -> None:
    """Verify FetchShowtimesFromSourceQuery.InputData rejects start after end."""
    with pytest.raises(ValueError, match="start_date must not be after end_date"):
        FetchShowtimesFromSourceQuery.InputData(
            cinema_id="cin-123",
            start_date=date(2026, 6, 8),
            end_date=date(2026, 6, 7),
        )


def test_input_data_allows_valid_input() -> None:
    """Verify FetchShowtimesFromSourceQuery.InputData accepts valid data."""
    request = FetchShowtimesFromSourceQuery.InputData(
        cinema_id="cin-123",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 7),
    )
    assert request.cinema_id == "cin-123"
    assert request.start_date == date(2026, 6, 7)
    assert request.end_date == date(2026, 6, 7)


def test_summary_rejects_negative_total_count() -> None:
    """Verify ImportScreeningsSummary rejects negative total_count."""
    with pytest.raises(ValueError, match="total_count must not be negative"):
        ImportScreeningsSummary(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=-1,
            imported_count=0,
            updated_count=0,
        )


def test_summary_rejects_negative_imported_count() -> None:
    """Verify ImportScreeningsSummary rejects negative imported_count."""
    with pytest.raises(ValueError, match="imported_count must not be negative"):
        ImportScreeningsSummary(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=0,
            imported_count=-1,
            updated_count=0,
        )


def test_summary_rejects_negative_updated_count() -> None:
    """Verify ImportScreeningsSummary rejects negative updated_count."""
    with pytest.raises(ValueError, match="updated_count must not be negative"):
        ImportScreeningsSummary(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=0,
            imported_count=0,
            updated_count=-1,
        )


def test_summary_rejects_negative_skipped_count() -> None:
    """Verify ImportScreeningsSummary rejects negative skipped_count."""
    with pytest.raises(ValueError, match="skipped_count must not be negative"):
        ImportScreeningsSummary(
            cinema_id="cin-123",
            cinema_name="Cinéma Beaubien",
            source_name="cinemacinema",
            screenings=(),
            total_count=0,
            imported_count=0,
            updated_count=0,
            skipped_count=-1,
        )


def test_summary_allows_valid() -> None:
    """Verify ImportScreeningsSummary accepts valid data."""
    screening = ImportedScreeningData(
        movie_title="Movie A",
        showtime="2026-06-07T19:30:00+00:00",
        imported=True,
    )
    result = ImportScreeningsSummary(
        cinema_id="cin-123",
        cinema_name="Cinéma Beaubien",
        source_name="cinemacinema",
        screenings=(screening,),
        total_count=1,
        imported_count=1,
        updated_count=0,
    )
    assert result.cinema_id == "cin-123"
    assert result.cinema_name == "Cinéma Beaubien"
    assert result.source_name == "cinemacinema"
    assert result.total_count == 1
    assert result.imported_count == 1
    assert result.updated_count == 0
    assert len(result.screenings) == 1


def test_imported_screening_data_rejects_empty_movie_title() -> None:
    """Verify ImportedScreeningData rejects empty movie_title."""
    with pytest.raises(ValueError, match="movie_title must not be empty"):
        ImportedScreeningData(
            movie_title="",
            showtime="2026-06-07T19:30:00+00:00",
            imported=True,
        )


def test_imported_screening_data_rejects_empty_showtime() -> None:
    """Verify ImportedScreeningData rejects empty showtime."""
    with pytest.raises(ValueError, match="showtime must not be empty"):
        ImportedScreeningData(
            movie_title="Movie A",
            showtime="",
            imported=True,
        )
