"""Guarded reschedules through the import/repository/PostgreSQL boundary."""

import asyncio
from dataclasses import replace
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, create_autospec
from zoneinfo import ZoneInfo

import asyncpg
import pytest
import pytest_asyncio

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.sources import (
    ShowtimeRow,
    SourceRegistry,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime
from marquise.infrastructure.postgres.gateways.cinema import PostgresCinemaGateway
from marquise.infrastructure.postgres.gateways.cinema_source_assignment import (
    PostgresCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.postgres.gateways.movie import PostgresMovieGateway
from marquise.infrastructure.postgres.gateways.screening import PostgresScreeningGateway
from marquise.infrastructure.postgres.gateways.screening_reader import (
    PostgresScreeningReadGateway,
)
from marquise.infrastructure.postgres.gateways.source_definition import (
    PostgresSourceDefinitionGateway,
)
from marquise.interface_adapters.repositories.cinema_repository import (
    PostgresCinemaRepository,
)
from marquise.interface_adapters.repositories.cinema_source_assignment_repository import (  # noqa: E501
    PostgresCinemaSourceAssignmentRepository,
)
from marquise.interface_adapters.repositories.movie_repository import (
    PostgresMovieRepository,
)
from marquise.interface_adapters.repositories.screening_repository import (
    PostgresScreeningRepository,
)
from support.movie_import import import_command

SCHEMA = '"marquise-test"'
CINEMA_NAME = "Cinéma Cineplex Odeon Quartier Latin"
LEGACY_CINEMA = "9fbeeb8d-b725-47b2-b10b-998331428d2b"
DIGGER = "66f77c4ca9c446fa863459d17123340f"
PARENTS = "c2ef9ab70a0b4a22b9e9490dfb633253"
OBSERVED = (
    ("a297eb7aee024c8a80fd84ceeab2de7d", "597122", DIGGER, "DIGGER", "13:00", "13:15"),
    ("cdc597ed360c4d1aac255dd4ea31ab7c", "597137", DIGGER, "DIGGER", "15:55", "16:10"),
    (
        "d597fb40a95d43d6baea3e2cf790db48",
        "597142",
        PARENTS,
        "Chers Parents",
        "14:00",
        "14:05",
    ),
    (
        "af6e45e97653455dbbac56047f28c5b1",
        "597152",
        PARENTS,
        "Chers Parents",
        "16:20",
        "16:25",
    ),
    (
        "62db2eac23d24e48b0dfa9df86c38f08",
        "597161",
        PARENTS,
        "Chers Parents",
        "18:30",
        "18:35",
    ),
)


def local(value: str) -> datetime:
    """Return a specified Montreal wall-clock time in UTC."""
    return (
        datetime.fromisoformat(value)
        .replace(tzinfo=ZoneInfo("America/Montreal"))
        .astimezone(UTC)
    )


@pytest_asyncio.fixture
async def import_chain(
    db_pool: asyncpg.Pool,
) -> tuple[ImportScreeningsCommand, MagicMock, PostgresScreeningRepository]:
    """Compose real persistence with only the external source registry mocked."""
    cinema = PostgresCinemaGateway(db_pool, "marquise-test")
    assignment = PostgresCinemaSourceAssignmentGateway(db_pool, "marquise-test")
    movies = PostgresMovieGateway(db_pool, "marquise-test")
    sources = PostgresSourceDefinitionGateway(db_pool, "marquise-test")
    for source in ("cineplex", "other-source"):
        await sources.save(source, source)
    for cinema_id, name in (("cin-001", CINEMA_NAME), ("cin-002", "Other Cinema")):
        await cinema.save(cinema_id, name, address=None, city=None)
        await assignment.assign(cinema_id, "cineplex")
    await movies.save("digger", "DIGGER", release_year=None)
    await movies.save("parents", "Chers Parents", release_year=None)
    registry = create_autospec(SourceRegistry, instance=True)
    screenings = PostgresScreeningRepository(
        PostgresScreeningGateway(db_pool, "marquise-test")
    )
    command = import_command(
        FetchScreeningsFromSourceQuery(
            PostgresCinemaRepository(cinema),
            PostgresCinemaSourceAssignmentRepository(assignment),
            registry,
        ),
        PostgresMovieRepository(movies),
        CreateScreeningsCommand(screenings),
    )
    return command, registry, screenings


async def run_import(
    command: ImportScreeningsCommand,
    registry: MagicMock,
    rows: list[ShowtimeRow],
    cinema_id: str = "cin-001",
) -> ImportScreeningsCommand.OutputData:
    """Supply deterministic source data to the actual import workflow."""
    registry.fetch_showtimes.return_value = rows
    return await command.execute(
        command.InputData(cinema_id, date(2026, 1, 1), date(2026, 12, 31))
    )


async def stored(
    db_pool: asyncpg.Pool,
    repository: PostgresScreeningRepository,
    cinema_id: str | None = None,
) -> list[Screening]:
    """Read stored screening IDs through the reader, then load domain entities."""
    page = await PostgresScreeningReadGateway(db_pool, "marquise-test").search(
        cinema_id=cinema_id
    )
    gateway = PostgresScreeningGateway(db_pool, "marquise-test")
    return [await read_screening(repository, gateway, row["id"]) for row in page.rows]


async def read_screening(
    repository: PostgresScreeningRepository,
    gateway: PostgresScreeningGateway,
    screening_id: str,
) -> Screening:
    """Read a persisted entity through its current import-candidate identity."""
    row = await gateway.find_by_id(screening_id)
    assert row is not None
    incoming = build_screening_identity(row)
    candidates = await repository.read_import_candidates(incoming)
    return next(candidate for candidate in candidates if candidate.id == incoming.id)


def build_screening_identity(row: dict) -> Screening:
    """Build the identity used to read a persisted screening's candidates."""
    return Screening(
        id=ScreeningId(row["id"]),
        movie=Movie(id=MovieId(row["movie_id"]), title=row["movie__title"]),
        cinema=Cinema(id=CinemaId(row["cinema_id"]), name=row["cinema__name"]),
        showtime=Showtime(row["showtime"].replace(tzinfo=UTC)),
        external_id=row["external_id"],
    )


async def seed_legacy_cineplex_screenings(db_pool: asyncpg.Pool) -> None:
    """Reproduce verified historical IDs, times and stored Cineplex source links."""
    cinema = PostgresCinemaGateway(db_pool, "marquise-test")
    assignment = PostgresCinemaSourceAssignmentGateway(db_pool, "marquise-test")
    movies = PostgresMovieGateway(db_pool, "marquise-test")
    screenings = PostgresScreeningGateway(db_pool, "marquise-test")
    async with db_pool.acquire() as connection:
        await connection.execute(f"DELETE FROM {SCHEMA}.movies")
    await cinema.save(LEGACY_CINEMA, CINEMA_NAME, address=None, city=None)
    await assignment.assign(LEGACY_CINEMA, "cineplex")
    await movies.save(DIGGER, "DIGGER", release_year=None)
    await movies.save(PARENTS, "Chers Parents", release_year=None)
    for screening_id, external_id, movie_id, _, old, _ in OBSERVED:
        await screenings.save(
            screening_id,
            movie_id,
            LEGACY_CINEMA,
            local(f"2026-10-07T{old}"),
            external_id,
            ticket_url=(
                "https://apis.cineplex.com/prod/ticketing/api/v1/routing/redirect-to-ticketing"
                f"?VistaSessionId={external_id}&LocationId=9172"
            ),
            source_name="cineplex",
        )


@pytest.mark.asyncio
async def test_all_five_legacy_reschedules_preserve_identity(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
) -> None:
    """Verified historical rows move in place and reimport without duplicates."""
    command, registry, repository = import_chain
    await seed_legacy_cineplex_screenings(db_pool)
    await screening_gateway.save(
        "other-cinema",
        DIGGER,
        "cin-002",
        local("2026-10-07T13:00"),
        "597122",
        source_name="other-source",
    )
    other_before = await read_screening(repository, screening_gateway, "other-cinema")
    before = await stored(db_pool, repository, LEGACY_CINEMA)
    assignments = PostgresCinemaSourceAssignmentGateway(db_pool, "marquise-test")
    await assignments.assign(LEGACY_CINEMA, "other-source")
    rows = [
        ShowtimeRow(title, local(f"2026-10-07T{new}"), external_id=external_id)
        for _, external_id, _, title, _, new in OBSERVED
    ]

    wrong_source = await run_import(command, registry, rows, LEGACY_CINEMA)
    assert wrong_source.skipped_count == 5
    assert await stored(db_pool, repository, LEGACY_CINEMA) == before
    await assignments.assign(LEGACY_CINEMA, "cineplex")
    result = await run_import(command, registry, rows, LEGACY_CINEMA)

    assert result.rescheduled_count == 5
    assert result.imported_count == result.updated_count == result.skipped_count == 0
    after = await stored(db_pool, repository, LEGACY_CINEMA)
    assert {str(row.id) for row in after} == {str(row.id) for row in before}
    assert {row.showtime.value for row in after} == {row.showtime for row in rows}
    assert (
        await read_screening(repository, screening_gateway, "other-cinema")
        == other_before
    )
    repeated = await run_import(command, registry, rows, LEGACY_CINEMA)
    assert repeated.updated_count == 5
    assert (
        repeated.rescheduled_count
        == repeated.imported_count
        == repeated.skipped_count
        == 0
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("old", "new", "accepted"),
    [
        ("2026-03-09T00:30", "2026-03-08T18:00", False),
        ("2026-11-01T23:30", "2026-11-01T18:00", True),
        ("2026-10-08T00:00", "2026-10-07T23:59", False),
        ("2026-10-06T23:59", "2026-10-07T00:00", False),
    ],
)
async def test_dst_and_cross_day_refusal(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    old: str,
    new: str,
    accepted: bool,
) -> None:
    """Actual persisted times obey Montreal days on DST and midnight boundaries."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner", "digger", "cin-001", local(old), "shared", source_name="cineplex"
    )
    before = await read_screening(repository, screening_gateway, "owner")

    result = await run_import(
        command, registry, [ShowtimeRow("DIGGER", local(new), external_id="shared")]
    )

    assert result.rescheduled_count == int(accepted)
    assert result.skipped_count == int(not accepted)
    after = await read_screening(repository, screening_gateway, "owner")
    assert after.showtime.value == (local(new) if accepted else before.showtime.value)
    assert after.id == before.id


async def wait_for_screening_lock(connection: asyncpg.Connection) -> None:
    """Wait for a real contending Screening statement, not a scheduling guess."""
    async with asyncio.timeout(5):
        while True:
            await connection.execute("SELECT pg_stat_clear_snapshot()")
            if await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_stat_activity "
                "WHERE pid <> pg_backend_pid() AND wait_event_type = 'Lock' "
                "AND query LIKE '%screenings%')"
            ):
                return
            await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_dst_fold_batch_preserves_persisted_owner(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
) -> None:
    """Two fold instants for one native ID refuse the batch without moving its owner."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-11-01T00:30"),
        "shared",
        source_name="cineplex",
    )
    before = await read_screening(repository, screening_gateway, "owner")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/Montreal"), fold=0)
    result = await run_import(
        command,
        registry,
        [
            ShowtimeRow("DIGGER", first, external_id="shared"),
            ShowtimeRow("DIGGER", first.replace(fold=1), external_id="shared"),
        ],
    )

    assert result.skipped_count == 2
    assert result.rescheduled_count == 0
    assert await read_screening(repository, screening_gateway, "owner") == before


@pytest.mark.asyncio
@pytest.mark.parametrize("external_id", [None, ""])
async def test_missing_native_id_cannot_reschedule_legacy_blank_owner(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
    external_id: str | None,
) -> None:
    """ID-less imports create a new performance without moving a legacy blank owner."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner", "digger", "cin-001", local("2026-10-07T13:00"), source_name="cineplex"
    )
    async with db_pool.acquire() as connection:
        await connection.execute(
            f"UPDATE {SCHEMA}.screenings SET external_id='' WHERE id='owner'"
        )
    before = await read_screening(repository, screening_gateway, "owner")
    result = await run_import(
        command,
        registry,
        [ShowtimeRow("DIGGER", local("2026-10-07T13:15"), external_id=external_id)],
    )
    assert result.imported_count == 1
    assert result.rescheduled_count == 0
    assert await read_screening(repository, screening_gateway, "owner") == before


@pytest.mark.asyncio
async def test_import_sees_identity_committed_while_insert_waits(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    db_pool: asyncpg.Pool,
) -> None:
    """A concurrent insert matched after waiting is read with a fresh snapshot."""
    command, registry, repository = import_chain
    rows = [ShowtimeRow("DIGGER", local("2026-10-07T13:15"), external_id="shared")]
    pending: asyncio.Task[ImportScreeningsCommand.OutputData] | None = None
    try:
        async with db_pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    f"INSERT INTO {SCHEMA}.screenings "
                    "(id, cinema_id, movie_id, showtime, external_id, source_name) "
                    "VALUES ('concurrent', 'cin-001', 'digger', $1, "
                    "'shared', 'cineplex')",
                    local("2026-10-07T13:15").replace(tzinfo=None),
                )
                pending = asyncio.create_task(run_import(command, registry, rows))
                await wait_for_screening_lock(connection)
        result = await asyncio.wait_for(pending, timeout=5)
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)

    assert result.updated_count == 1
    assert result.imported_count == result.skipped_count == 0
    saved = await stored(db_pool, repository, "cin-001")
    assert [str(row.id) for row in saved] == ["concurrent"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "refusal", ["movie", "source", "unknown", "target", "ambiguous"]
)
async def test_refused_reschedule_preserves_every_row(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
    caplog: pytest.LogCaptureFixture,
    refusal: str,
) -> None:
    """Refused reuse, provenance, collisions and ambiguity preserve existing rows."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name=None if refusal == "unknown" else "cineplex",
        room="Old room",
    )
    rows = [
        ShowtimeRow(
            "Chers Parents" if refusal == "movie" else "DIGGER",
            local("2026-10-07T13:15"),
            external_id="shared",
            room="New room",
        )
    ]
    if refusal == "source":
        await PostgresCinemaSourceAssignmentGateway(db_pool, "marquise-test").assign(
            "cin-001", "other-source"
        )
    if refusal == "target":
        await screening_gateway.save(
            "unrelated", "digger", "cin-001", rows[0].showtime, room="Unrelated room"
        )
    if refusal == "ambiguous":
        rows.append(replace(rows[0], showtime=local("2026-10-07T14:00")))
    before = await stored(db_pool, repository, "cin-001")

    result = await run_import(command, registry, rows)

    assert result.skipped_count == len(rows)
    assert (
        result.imported_count == result.updated_count == result.rescheduled_count == 0
    )
    after = await stored(db_pool, repository, "cin-001")
    assert after == before
    assert "shared" in caplog.text
    if refusal in ("source", "unknown"):
        assert "provenance" in caplog.text


@pytest.mark.asyncio
async def test_same_time_source_takeover_is_refused(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A same-time import cannot relabel another source's row to enable reschedules."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
        room="Old room",
    )
    before = await read_screening(repository, screening_gateway, "owner")
    await PostgresCinemaSourceAssignmentGateway(db_pool, "marquise-test").assign(
        "cin-001", "other-source"
    )
    result = await run_import(
        command,
        registry,
        [
            ShowtimeRow(
                "DIGGER", before.showtime.value, external_id="shared", room="New room"
            )
        ],
    )

    assert result.skipped_count == 1
    assert await read_screening(repository, screening_gateway, "owner") == before
    assert "source provenance" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("external_id", [None, ""])
async def test_missing_external_id_never_moves_an_existing_screening(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    external_id: str | None,
) -> None:
    """Missing IDs remain supported as new performances, not guesses at reschedules."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
    )
    before = await read_screening(repository, screening_gateway, "owner")
    result = await run_import(
        command,
        registry,
        [ShowtimeRow("DIGGER", local("2026-10-07T13:15"), external_id=external_id)],
    )

    assert result.rescheduled_count == 0
    assert result.imported_count == 1
    assert await read_screening(repository, screening_gateway, "owner") == before


@pytest.mark.asyncio
@pytest.mark.parametrize("external_id", [None, ""])
async def test_idless_metadata_cannot_attest_a_retained_legacy_id(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
    external_id: str | None,
) -> None:
    """An ID-less source observation cannot authorize a later move of an old ID."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner", "digger", "cin-001", local("2026-10-07T13:00"), "shared"
    )
    await PostgresCinemaSourceAssignmentGateway(db_pool, "marquise-test").assign(
        "cin-001", "other-source"
    )
    metadata = await run_import(
        command,
        registry,
        [
            ShowtimeRow(
                "DIGGER",
                local("2026-10-07T13:00"),
                external_id=external_id,
                room="New room",
            )
        ],
    )
    assert metadata.updated_count == 1
    observed = await read_screening(repository, screening_gateway, "owner")
    assert observed.source_name is None
    assert observed.external_id == "shared"
    assert observed.room == "New room"

    moved = await run_import(
        command,
        registry,
        [ShowtimeRow("DIGGER", local("2026-10-07T13:15"), external_id="shared")],
    )
    assert moved.skipped_count == 1
    assert moved.rescheduled_count == 0
    assert await read_screening(repository, screening_gateway, "owner") == observed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cinema_id", "fields", "external_id", "eligible"),
    [
        ("cin-001", frozenset({"cinema_id"}), "shared", True),
        ("cin-002", frozenset({"cinema_id"}), "shared", False),
        ("cin-002", frozenset({"cinema_id", "external_id"}), "shared", False),
        ("cin-002", frozenset({"cinema_id", "external_id"}), "replacement", False),
    ],
)
async def test_manual_reparent_cannot_transfer_cinema_scoped_ownership(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
    cinema_id: str,
    fields: frozenset[str],
    external_id: str,
    eligible: bool,
) -> None:
    """A new Cinema/native-ID namespace needs fresh proof before an imported move."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
    )
    before = await read_screening(repository, screening_gateway, "owner")
    changed = await repository.replace(
        replace(
            before,
            cinema=Cinema(id=CinemaId(cinema_id), name="Cinema"),
            external_id=external_id,
        ),
        fields=fields,
    )
    await PostgresCinemaSourceAssignmentGateway(db_pool, "marquise-test").assign(
        cinema_id, "cineplex"
    )
    result = await run_import(
        command,
        registry,
        [ShowtimeRow("DIGGER", local("2026-10-07T13:15"), external_id=external_id)],
        cinema_id,
    )

    assert result.rescheduled_count == int(eligible)
    assert result.skipped_count == int(not eligible)
    assert changed.source_name == ("cineplex" if eligible else None)
    after = await read_screening(repository, screening_gateway, "owner")
    assert after.showtime.value == (
        local("2026-10-07T13:15") if eligible else changed.showtime.value
    )
    assert after.id == before.id


@pytest.mark.asyncio
async def test_external_id_change_without_source_witness_clears_provenance(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
) -> None:
    """Changing the native ID in the same cinema drops cineplex ownership."""
    _, _, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
    )
    before = await read_screening(repository, screening_gateway, "owner")

    changed = await repository.replace(
        replace(before, external_id="replacement"),
        fields=frozenset({"external_id"}),
    )

    assert changed.id == before.id
    assert changed.external_id == "replacement"
    assert changed.source_name is None


@pytest.mark.asyncio
async def test_same_cinema_replace_keeps_provenance_when_native_id_is_unchanged(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
) -> None:
    """Restating the current cinema without changing the native ID keeps ownership."""
    _, _, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
    )
    before = await read_screening(repository, screening_gateway, "owner")

    changed = await repository.replace(before, fields=frozenset({"cinema_id"}))

    assert changed.id == before.id
    assert changed.external_id == "shared"
    assert changed.source_name == "cineplex"


@pytest.mark.asyncio
async def test_failed_reschedule_preserves_old_values(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
) -> None:
    """A failing SQL write rolls back all time and metadata changes."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
        room="Old room",
    )
    before = await read_screening(repository, screening_gateway, "owner")
    async with db_pool.acquire() as connection:
        await connection.execute(f"""
            CREATE FUNCTION {SCHEMA}.fail_reschedule() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'Injected reschedule failure'; END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER fail_reschedule AFTER UPDATE ON {SCHEMA}.screenings
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.fail_reschedule();
        """)
    try:
        with pytest.raises(asyncpg.RaiseError, match="Injected reschedule failure"):
            await run_import(
                command,
                registry,
                [
                    ShowtimeRow(
                        "DIGGER",
                        local("2026-10-07T13:15"),
                        external_id="shared",
                        room="New room",
                    )
                ],
            )
        assert await read_screening(repository, screening_gateway, "owner") == before
    finally:
        async with db_pool.acquire() as connection:
            await connection.execute(
                f"DROP TRIGGER fail_reschedule ON {SCHEMA}.screenings; "
                f"DROP FUNCTION {SCHEMA}.fail_reschedule();"
            )


@pytest.mark.asyncio
async def test_concurrent_source_change_refuses_waiting_reschedule(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
) -> None:
    """Eligibility is rechecked after a lock wait instead of overwriting a new owner."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
    )
    pending: asyncio.Task[ImportScreeningsCommand.OutputData] | None = None
    try:
        async with db_pool.acquire() as connection:
            async with connection.transaction():
                await connection.fetchrow(
                    f"SELECT id FROM {SCHEMA}.screenings WHERE id = 'owner' FOR UPDATE"
                )
                pending = asyncio.create_task(
                    run_import(
                        command,
                        registry,
                        [
                            ShowtimeRow(
                                "DIGGER",
                                local("2026-10-07T13:15"),
                                external_id="shared",
                            )
                        ],
                    )
                )
                await wait_for_screening_lock(connection)
                await connection.execute(
                    f"UPDATE {SCHEMA}.screenings SET source_name = 'other-source' "
                    "WHERE id = 'owner'"
                )
        result = await asyncio.wait_for(pending, timeout=5)
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)

    assert result.skipped_count == 1
    saved = await read_screening(repository, screening_gateway, "owner")
    assert saved.showtime.value == local("2026-10-07T13:00")
    assert saved.source_name == "other-source"


@pytest.mark.asyncio
async def test_concurrent_imports_move_one_screening_without_duplicates(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
) -> None:
    """Concurrent requests for one move preserve its ID and unrelated Screenings."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
        room="Old room",
    )
    await screening_gateway.save(
        "unrelated",
        "parents",
        "cin-001",
        local("2026-10-07T13:00"),
        "other",
        source_name="cineplex",
        room="Unrelated room",
    )
    unrelated = await read_screening(repository, screening_gateway, "unrelated")
    rows = [
        ShowtimeRow(
            "DIGGER", local("2026-10-07T13:15"), external_id="shared", room="New room"
        )
    ]

    results = await asyncio.gather(
        run_import(command, registry, rows), run_import(command, registry, rows)
    )

    assert sum(result.total_count for result in results) == 2
    assert sum(result.skipped_count + result.imported_count for result in results) == 0
    owner = await read_screening(repository, screening_gateway, "owner")
    assert owner.showtime.value == local("2026-10-07T13:15")
    assert owner.room == "New room"
    assert len(await stored(db_pool, repository, "cin-001")) == 2
    assert await read_screening(repository, screening_gateway, "unrelated") == unrelated


@pytest.mark.asyncio
async def test_concurrent_target_arrival_rolls_back_reschedule(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    screening_gateway: PostgresScreeningGateway,
    db_pool: asyncpg.Pool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A target inserted during contention is never overwritten or merged."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
    )
    before = await read_screening(repository, screening_gateway, "owner")
    pending: asyncio.Task[ImportScreeningsCommand.OutputData] | None = None
    try:
        async with db_pool.acquire() as connection:
            async with connection.transaction():
                await connection.fetchrow(
                    f"SELECT id FROM {SCHEMA}.screenings WHERE id = 'owner' FOR UPDATE"
                )
                pending = asyncio.create_task(
                    run_import(
                        command,
                        registry,
                        [
                            ShowtimeRow(
                                "DIGGER",
                                local("2026-10-07T13:15"),
                                external_id="shared",
                            )
                        ],
                    )
                )
                await wait_for_screening_lock(connection)
                await connection.execute(
                    f"INSERT INTO {SCHEMA}.screenings "
                    "(id, movie_id, cinema_id, showtime, room) "
                    "VALUES ('target', 'digger', 'cin-001', $1, 'Unrelated room')",
                    local("2026-10-07T13:15").replace(tzinfo=None),
                )
        result = await asyncio.wait_for(pending, timeout=5)
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)

    assert result.skipped_count == 1
    assert "rescheduled identity" in caplog.text
    assert await read_screening(repository, screening_gateway, "owner") == before
    target = await read_screening(repository, screening_gateway, "target")
    assert target.external_id is None
    assert target.room == "Unrelated room"


@pytest.mark.asyncio
async def test_source_provenance_requires_a_registered_source(
    db_pool: asyncpg.Pool,
) -> None:
    """Rows start with unknown provenance; deleting the source clears it."""
    async with db_pool.acquire() as connection:
        await connection.execute(
            f"INSERT INTO {SCHEMA}.cinemas (id,name) VALUES ('cin','Cinema'); "
            f"INSERT INTO {SCHEMA}.movies (id,title) VALUES ('mov','Movie'); "
            f"INSERT INTO {SCHEMA}.source_definitions (name,display_name) "
            "VALUES ('cineplex','Cineplex'); "
            f"INSERT INTO {SCHEMA}.screenings (id,cinema_id,movie_id,showtime) "
            "VALUES ('legacy','cin','mov','2026-10-07 17:00');"
        )
        source_name = f"SELECT source_name FROM {SCHEMA}.screenings"
        assert await connection.fetchval(source_name) is None
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await connection.execute(
                f"UPDATE {SCHEMA}.screenings SET source_name='unregistered'"
            )
        await connection.execute(
            f"UPDATE {SCHEMA}.screenings SET source_name='cineplex'"
        )
        await connection.execute(f"DELETE FROM {SCHEMA}.source_definitions")
        assert await connection.fetchval(source_name) is None


@pytest.mark.asyncio
async def test_ambiguous_persisted_ownership_never_reschedules_a_candidate(
    import_chain: tuple[
        ImportScreeningsCommand, MagicMock, PostgresScreeningRepository
    ],
    db_pool: asyncpg.Pool,
    screening_gateway: PostgresScreeningGateway,
) -> None:
    """Damaged uniqueness cannot make reschedule pick an arbitrary owner."""
    command, registry, repository = import_chain
    await screening_gateway.save(
        "owner",
        "digger",
        "cin-001",
        local("2026-10-07T13:00"),
        "shared",
        source_name="cineplex",
    )
    async with db_pool.acquire() as connection:
        await connection.execute(
            f"ALTER TABLE {SCHEMA}.screenings "
            "DROP CONSTRAINT screenings_external_id_key"
        )
    try:
        await screening_gateway.save(
            "ambiguous",
            "digger",
            "cin-001",
            local("2026-10-07T14:00"),
            "shared",
            source_name="cineplex",
        )
        before = await stored(db_pool, repository)
        result = await run_import(
            command,
            registry,
            [ShowtimeRow("DIGGER", local("2026-10-07T13:15"), external_id="shared")],
        )
        assert result.skipped_count == 1
        assert result.rescheduled_count == 0
        assert await stored(db_pool, repository) == before
    finally:
        async with db_pool.acquire() as connection:
            await connection.execute(
                f"DELETE FROM {SCHEMA}.screenings WHERE id='ambiguous'"
            )
            await connection.execute(
                f"ALTER TABLE {SCHEMA}.screenings "
                "ADD CONSTRAINT screenings_external_id_key "
                "UNIQUE (cinema_id, external_id)"
            )
