"""The showtimes date range dependency returns timezone-aware dates."""

from datetime import UTC, datetime, timedelta, timezone

from marquise_api.routers._dependencies import resolve_showtimes_date_range


def test_naive_dates_resolve_to_utc() -> None:
    """Naive dates gain UTC, so they match their explicit UTC equivalents."""
    date_range = resolve_showtimes_date_range(
        from_=datetime(2026, 6, 27), to=datetime(2026, 6, 28, 18)
    )
    assert date_range == (
        datetime(2026, 6, 27, tzinfo=UTC),
        datetime(2026, 6, 28, 18, tzinfo=UTC),
    )


def test_explicit_offsets_are_kept() -> None:
    """Dates that carry an offset come back unchanged."""
    montreal_summer = timezone(timedelta(hours=-4))
    start = datetime(2026, 6, 27, 18, tzinfo=montreal_summer)
    end = datetime(2026, 6, 28, 18, tzinfo=montreal_summer)
    resolved_from, resolved_to = resolve_showtimes_date_range(from_=start, to=end)
    assert (resolved_from, resolved_to) == (start, end)
    assert resolved_from.tzinfo == montreal_summer
    assert resolved_to.tzinfo == montreal_summer
