"""Small live checks, run separately from deterministic integration tests."""

from marquise.infrastructure.sources.cinemacinema.gateways.source import (
    _fetch_schedule,
)
from marquise.infrastructure.sources.cineplex.gateways.source import (
    SHOWTIMES_URL,
    CineplexSource,
    _fetch_json,
)


def test_cineplex_showtimes_connection() -> None:
    """The live Cineplex endpoint accepts the resolved key and returns JSON."""
    source = CineplexSource()
    response = _fetch_json(
        f"{SHOWTIMES_URL}?LocationId=9172", api_key=source._resolve_api_key()
    )
    assert isinstance(response, list)
    assert any(
        isinstance(theatre, dict) and theatre.get("theatreId") == 9172
        for theatre in response
    )


def test_cinemacinema_schedule_connection() -> None:
    """The live CinemaCinema schedule remains reachable and recognizable."""
    response = _fetch_schedule()
    assert response.get("cmDates")
