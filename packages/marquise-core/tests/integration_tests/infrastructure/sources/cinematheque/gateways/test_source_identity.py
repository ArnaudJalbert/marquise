"""Replay captured cinema evidence over loopback HTTP without a database."""

from pathlib import Path

import pytest

from marquise.infrastructure.sources.cinematheque.gateways import source as cinema
from marquise.infrastructure.sources.cineplex.gateways import source as cineplex

_FIXTURES = Path(__file__).parents[5] / "fixtures" / "source_identity"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "detail_state", ["available", "missing", "challenge", "unlinked"]
)
async def test_carrie_recovers_linked_evidence_with_ticketing_fallback(
    detail_state: str,
    local_http: tuple[str, dict[str, tuple[bytes, str]], list[tuple[str, str | None]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recover Carrie facts by performance ID or keep usable ticketing data."""
    base, routes, requests = local_http
    monkeypatch.setattr(cinema, "BASE_URL", base + "/tickets/")
    monkeypatch.setattr(cinema, "CINEMA_URL", base + "/en/cinema/")
    schedule = (_FIXTURES / "carrie-schedule.html").read_bytes()
    routes["/tickets/?schdate=2026-10-30"] = (schedule, "text/html")
    index = (_FIXTURES / "carrie-index.html").read_bytes()
    if detail_state == "unlinked":
        index = index.replace(b"perfix=14321", b"perfix=99999")
    routes["/en/cinema/"] = (index, "text/html")
    if detail_state == "available":
        routes["/en/cinema/carrie/"] = (
            (_FIXTURES / "carrie-detail.html").read_bytes(),
            "text/html",
        )
    elif detail_state == "challenge":
        routes["/en/cinema/carrie/"] = (b"<html>Challenge</html>", "text/html")

    source = cinema.CinemathequeSource()
    # Exercise the captured schedule parser independently of today's bootstrap date.
    rows = cinema._parse_movie_data(
        cinema._extract_movie_data(schedule.decode()), "2026-10-30"
    )
    assert rows[0] == {
        "movie_title": "Carrie (VOSTF)",
        "showtime": "2026-10-31T00:30:00+00:00",
        "identifier": "2026-10-30|242894996",
        "external_id": "14321",
        "ticket_url": base
        + "/tickets/?schdate=2026-10-30&film=242894996&aud=1&ptime=20:30&ptype=G",
        "room": "SALLE 1",
        "language": "VOSTF",
    }
    detail = await source.fetch_movie_detail(rows[0]["identifier"])
    assert detail is not None
    assert detail["duration_minutes"] == 98
    assert detail["rating"] == "En attente de classement"
    if detail_state == "available":
        assert detail["release_year"] == 1976
        assert detail["directors"] == ["Brian De Palma"]
        assert detail["cast"] == ["Sissy Spacek", "Piper Laurie", "Amy Irving"]
    else:
        assert "release_year" not in detail
        assert "directors" not in detail
        assert "cast" not in detail
    expected = ["/tickets/?schdate=2026-10-30", "/en/cinema/"]
    if detail_state != "unlinked":
        expected.append("/en/cinema/carrie/")
    assert [path for path, _ in requests] == expected


@pytest.mark.asyncio
async def test_la_bola_negra_splits_only_cineplex_director_credits(
    local_http: tuple[str, dict[str, tuple[bytes, str]], list[tuple[str, str | None]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read both source directors without changing the source title or cast."""
    base, routes, requests = local_http
    monkeypatch.setattr(cineplex, "MOVIE_DETAIL_TPL", base + "/movie/{slug}")
    routes["/movie/la-bola-negra"] = (
        (_FIXTURES / "la-bola-negra.html").read_bytes(),
        "text/html",
    )
    detail = await cineplex.CineplexSource().fetch_movie_detail("la-bola-negra")
    assert detail is not None
    assert detail["directors"] == ["Javier Calvo", "Javier Ambrossi"]
    assert detail["duration_minutes"] == 160
    assert detail["release_year"] == 2026
    assert requests == [("/movie/la-bola-negra", None)]
