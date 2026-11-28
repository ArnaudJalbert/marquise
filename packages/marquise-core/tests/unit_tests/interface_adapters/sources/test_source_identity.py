"""Source facts reach existing structured import inputs through injected gateways."""

from datetime import UTC, date, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
)
from marquise.domain.entities import Cinema, CinemaSourceAssignment, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName
from marquise.interface_adapters.gateways.showtime_source import (
    ShowtimeSource,
)
from marquise.interface_adapters.sources.cinematheque import (
    CinemathequeAdapter,
)
from marquise.interface_adapters.sources.scraper_source_registry import (
    ScraperSourceRegistry,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("available", [True, False])
async def test_source_evidence_reaches_structured_import_without_changing_screenings(
    available: bool,
) -> None:
    """Recovered facts and source-only fallback retain screening data."""
    gateway = create_autospec(ShowtimeSource, instance=True)
    title = "Carrie (VOSTF)"
    identifier = "2026-10-30|242894996"
    ticket = "https://omniwebticketing6.com/cinematheque/?film=242894996&perfix=14321"
    gateway.fetch_showtimes.return_value = [
        {
            "movie_title": title,
            "showtime": "2026-10-31T00:30:00+00:00",
            "identifier": identifier,
            "external_id": "14321",
            "ticket_url": ticket,
            "room": "SALLE 1",
            "language": "VOSTF",
        }
    ]
    gateway.fetch_movie_detail.return_value = (
        {
            "release_year": 1976,
            "directors": ["Brian De Palma"],
            "cast": ["Sissy Spacek", "Piper Laurie", "Amy Irving"],
            "duration_minutes": 98,
        }
        if available
        else None
    )
    registry = ScraperSourceRegistry()
    registry.register("cinematheque", CinemathequeAdapter(gateway))
    cinema = Cinema(
        id=CinemaId(value="cin-cinematheque"), name="Cinémathèque québécoise"
    )
    source = SourceDefinition(
        name=SourceName(value="cinematheque"), display_name="Cinémathèque"
    )
    cinema_repository = create_autospec(CinemaRepository, instance=True)
    cinema_repository.find_by_id.return_value = cinema
    assignment_repository = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    assignment_repository.find_by_cinema_id.return_value = CinemaSourceAssignment(
        cinema=cinema, source=source
    )
    query = FetchScreeningsFromSourceQuery(
        cinema_repository, assignment_repository, registry
    )

    result = await query.execute(
        FetchScreeningsFromSourceQuery.InputData(
            cinema_id=str(cinema.id),
            start_date=date(2026, 10, 30),
            end_date=date(2026, 10, 30),
        )
    )

    (movie,) = result.movies
    assert movie.title == title
    assert movie.identifier == identifier
    assert movie.release_year == (1976 if available else None)
    assert movie.directors == (("Brian De Palma",) if available else None)
    assert movie.cast == (
        ("Sissy Spacek", "Piper Laurie", "Amy Irving") if available else None
    )
    assert movie.duration_minutes == (98 if available else None)
    (screening,) = result.screenings
    assert screening.movie_title == title
    assert screening.language == "VOSTF"
    assert screening.external_id == "14321"
    assert screening.ticket_url == ticket
    assert screening.room == "SALLE 1"
    assert screening.showtime == datetime(2026, 10, 31, 0, 30, tzinfo=UTC)
    gateway.fetch_movie_detail.assert_awaited_once_with(identifier=identifier)
    gateway.fetch_showtimes.assert_awaited_once()
