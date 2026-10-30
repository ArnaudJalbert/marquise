"""Source linkage refuses ambiguous and unrelated cinema pages."""

from pathlib import Path

import pytest

from marquise.infrastructure.sources.cinematheque.gateways.detail import (
    extract_detail,
    find_detail_url,
)

_FIXTURES = Path(__file__).parents[5] / "fixtures" / "source_identity"


@pytest.mark.parametrize(
    "date, performance", [("2026-10-29", "14321"), ("2026-10-30", "1432")]
)
def test_linkage_requires_exact_date_and_performance(
    date: str, performance: str
) -> None:
    """Similar IDs or a different date cannot link source evidence."""
    index = (_FIXTURES / "carrie-index.html").read_text()
    assert (
        find_detail_url(index, {(date, performance)}, "https://cinema.example/") is None
    )


def test_ambiguous_film_cards_do_not_supply_identity_evidence() -> None:
    """Two different pages linked to the same modal retain the ticketing fallback."""
    index = (_FIXTURES / "carrie-index.html").read_text()
    index += index.replace("/en/cinema/carrie/", "/en/cinema/different-film/")
    assert (
        find_detail_url(index, {("2026-10-30", "14321")}, "https://cinema.example/")
        is None
    )


def test_unusable_details_do_not_invent_missing_facts() -> None:
    """Empty or invalid fields cannot replace usable ticketing facts."""
    detail = (_FIXTURES / "carrie-detail.html").read_text()
    detail = detail.replace("1976", "unknown").replace("98 min", "unknown")
    detail = detail.replace("Brian De Palma", "").replace(
        "Sissy Spacek, Piper Laurie, Amy Irving", ""
    )
    assert extract_detail(detail) == {}


def test_cinema_names_are_not_globally_split_on_and() -> None:
    """Only the provider's explicit comma-separated credits are shaped here."""
    detail = (_FIXTURES / "carrie-detail.html").read_text()
    detail = detail.replace("Brian De Palma", "Alex and Family")
    assert extract_detail(detail)["directors"] == ["Alex and Family"]
