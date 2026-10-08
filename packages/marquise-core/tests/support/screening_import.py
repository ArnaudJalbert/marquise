"""Compose the real import workflow with deterministic repository/source doubles."""

from datetime import UTC, date, datetime
from unittest.mock import create_autospec

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    MovieRepository,
    ScreeningRepository,
    SourceRegistryQuery,
)
from marquise.application.repositories.source_registry_query import ShowtimeRow
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.domain.entities import (
    Cinema,
    CinemaSourceAssignment,
    Movie,
    Screening,
    SourceDefinition,
)
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
    SourceName,
)


def owner() -> Screening:
    """Return a verified source-owned performance."""
    return Screening(
        id=ScreeningId("stable"),
        cinema=Cinema(id=CinemaId("cin"), name="Cinema"),
        movie=Movie(id=MovieId("movie"), title="Film"),
        showtime=Showtime(datetime(2026, 10, 7, 17, tzinfo=UTC)),
        external_id="native",
        source_name="cineplex",
        room="old",
    )


async def run_import(
    repository: ScreeningRepository, incoming: Screening, *others: Screening
) -> ImportScreeningsCommand.OutputData:
    """Execute real use cases with mocked external source and unrelated repositories."""
    rows = (incoming, *others)
    cinemas = create_autospec(CinemaRepository, instance=True)
    cinemas.find_by_id.return_value = incoming.cinema
    assignments = create_autospec(CinemaSourceAssignmentRepository, instance=True)
    assignments.find_by_cinema_id.return_value = CinemaSourceAssignment(
        cinema=incoming.cinema,
        source=SourceDefinition(
            name=SourceName(incoming.source_name or "cineplex"), display_name="Source"
        ),
    )
    source = create_autospec(SourceRegistryQuery, instance=True)
    source.fetch_showtimes.return_value = [
        ShowtimeRow(
            row.movie.title,
            row.showtime.value,
            external_id=row.external_id,
            room=row.room,
            ticket_url=row.ticket_url,
            language=row.language,
        )
        for row in rows
    ]
    movies = create_autospec(MovieRepository, instance=True)
    movies.find_by_titles.return_value = list(
        {row.movie.id: row.movie for row in rows}.values()
    )
    command = ImportScreeningsCommand(
        FetchScreeningsFromSourceQuery(cinemas, assignments, source),
        CreateMissingMoviesCommand(movies),
        CreateScreeningsCommand(repository),
    )
    return await command.execute(
        command.InputData(str(incoming.cinema.id), date(2026, 1, 1), date(2026, 12, 31))
    )
