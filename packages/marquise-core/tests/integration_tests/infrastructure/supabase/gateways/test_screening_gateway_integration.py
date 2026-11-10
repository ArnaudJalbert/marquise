"""Integration tests for SupabaseScreeningGateway."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import asyncpg
import pytest

from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.infrastructure.supabase.gateways.cinema import (
    SupabaseCinemaGateway,
)
from marquise.infrastructure.supabase.gateways.movie import (
    SupabaseMovieGateway,
)
from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)
from marquise.infrastructure.supabase.gateways.screening_reader import (
    SupabaseScreeningReadGateway,
)
from marquise.infrastructure.supabase.gateways.source_definition import (
    SupabaseSourceDefinitionGateway,
)
from marquise.interface_adapters.repositories.protocols.base import GatewayError
from marquise.interface_adapters.repositories.protocols.screening import (
    ScreeningExternalIdConflictGatewayError,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


async def _seed_parents(
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Create parent rows needed for FK constraints."""
    await gateway.save(cinema_id="cin-001", name="Cinema One", address=None, city=None)
    await gateway.save(
        cinema_id="cin-003", name="Cinema Three", address=None, city=None
    )
    await gateway.save(cinema_id="cin-004", name="Cinema Four", address=None, city=None)
    await movie_gateway.save(movie_id="mov-001", title="Movie A", release_year=None)
    await movie_gateway.save(movie_id="mov-002", title="Movie B", release_year=None)
    await movie_gateway.save(movie_id="mov-003", title="Movie C", release_year=None)


@pytest.mark.asyncio
async def test_save_and_find_by_id(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify a screening can be saved and then retrieved by ID."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    result = await screening_gateway.save(
        screening_id="scr-001",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=showtime,
    )
    assert result.inserted is True
    assert result.row["id"] == "scr-001"
    assert result.row["movie_id"] == "mov-001"
    assert result.row["cinema_id"] == "cin-001"

    found = await screening_gateway.find_by_id("scr-001")
    assert found is not None
    assert found["movie__id"] == "mov-001"
    assert found["cinema__id"] == "cin-001"


@pytest.mark.asyncio
async def test_checked_write_preserves_id_without_eligibility_policy(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Storage accepts a checked cross-day change without source/day policy."""
    await _seed_parents(gateway, movie_gateway)
    await source_definition_gateway.save(
        name="cineplex", display_name="Cineplex", description=None
    )
    saved = await screening_gateway.save(
        screening_id="scr-reschedule",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 17, 0, tzinfo=UTC),
        external_id="show-1",
        source_name="cineplex",
    )

    proposed = dict(saved.row, showtime=datetime(2026, 6, 8, 17, 15), source_name=None)
    result = await screening_gateway.commit_import(
        proposed,
        incoming=proposed,
        expected=(saved.row,),
    )

    assert result is not None
    assert result["id"] == "scr-reschedule"
    assert result["showtime"] == datetime(2026, 6, 8, 17, 15)
    assert (await screening_gateway.find_by_id("scr-reschedule"))["showtime"] == (
        datetime(2026, 6, 8, 17, 15)
    )


@pytest.mark.asyncio
async def test_import_reschedules_idempotently_and_preserves_conflicts(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    source_definition_gateway: SupabaseSourceDefinitionGateway,
    db_pool: asyncpg.Pool,
) -> None:
    """Import chain moves same-source showtimes and refuses source changes."""
    await _seed_parents(gateway, movie_gateway)
    for name in ("cineplex", "other-source"):
        await source_definition_gateway.save(
            name=name, display_name=name, description=None
        )
    command = CreateScreeningsCommand(SupabaseScreeningRepository(screening_gateway))
    reader = SupabaseScreeningReadGateway(db_pool, "marquise-test")

    def row(
        showtime: datetime, source_name: str = "cineplex"
    ) -> CreateScreeningsCommand.ScreeningInput:
        return command.ScreeningInput(
            movie_id="mov-001",
            movie_title="Movie A",
            cinema_id="cin-001",
            cinema_name="Cinema One",
            showtime=showtime,
            external_id="show-1",
            source_name=source_name,
        )

    first = await command.execute(
        command.InputData((row(datetime(2026, 6, 7, 17, tzinfo=UTC)),))
    )
    initial_rows = await reader.search(cinema_id="cin-001")
    initial_id = initial_rows.rows[0]["id"]
    moved = await command.execute(
        command.InputData((row(datetime(2026, 6, 7, 17, 15, tzinfo=UTC)),))
    )
    repeated = await command.execute(
        command.InputData((row(datetime(2026, 6, 7, 17, 15, tzinfo=UTC)),))
    )
    refused = await command.execute(
        command.InputData(
            (row(datetime(2026, 6, 7, 17, 30, tzinfo=UTC), "other-source"),)
        )
    )

    assert first.imported_count == 1
    assert moved.rescheduled_count == 1
    assert repeated.updated_count == 1
    assert refused.skipped_count == 1
    rows = await reader.search(cinema_id="cin-001")
    assert [(r["id"], r["showtime"]) for r in rows.rows] == [
        (initial_id, datetime(2026, 6, 7, 17, 15))
    ]


@pytest.mark.asyncio
async def test_find_by_id_missing(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify find_by_id returns None for a non-existent ID."""
    found = await screening_gateway.find_by_id("scr-missing")
    assert found is None


@pytest.mark.asyncio
async def test_save_upserts_on_unique_key_conflict(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify save returns the existing row on conflict."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 9, 19, 30, 0, tzinfo=UTC)
    await screening_gateway.save(
        screening_id="scr-006",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=showtime,
    )

    saved = await screening_gateway.save(
        screening_id="scr-007",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=showtime,
    )
    assert saved.row["id"] == "scr-006"
    assert saved.inserted is False

    new_id = await screening_gateway.find_by_id("scr-007")
    assert new_id is None


@pytest.mark.asyncio
async def test_save_raises_gateway_error_on_external_id_conflict(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify save raises GatewayError when external_id collides across rows.

    Reproduces the Cineplex bug: an external_id reused for a different
    (cinema_id, movie_id, showtime) can't be resolved by the composite-key
    ON CONFLICT clause and must surface as a GatewayError instead of a raw
    asyncpg.UniqueViolationError.
    """
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-008",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=datetime(2026, 6, 11, 19, 30, 0, tzinfo=UTC),
        external_id="ext-conflict",
    )

    with pytest.raises(ScreeningExternalIdConflictGatewayError, match="ext-conflict"):
        await screening_gateway.save(
            screening_id="scr-009",
            movie_id="mov-002",
            cinema_id="cin-004",
            showtime=datetime(2026, 6, 12, 21, 0, 0, tzinfo=UTC),
            external_id="ext-conflict",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_target", [False, True])
async def test_import_skips_external_id_conflict_and_preserves_existing_data(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    existing_target: bool,
) -> None:
    """Real command/repository/gateway chain skips collisions and imports other rows."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 12, 21, tzinfo=UTC)
    await screening_gateway.save(
        screening_id="owner",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=showtime,
        external_id="494935",
    )
    if existing_target:
        await screening_gateway.save(
            screening_id="target",
            movie_id="mov-002",
            cinema_id="cin-004",
            showtime=showtime,
            external_id="old-id",
            room="Old room",
        )
    owner_before = await screening_gateway.find_by_id("owner")
    target_before = await screening_gateway.find_by_id("target")
    command = CreateScreeningsCommand(SupabaseScreeningRepository(screening_gateway))

    result = await command.execute(
        command.InputData(
            screenings=(
                command.ScreeningInput(
                    movie_id="mov-002",
                    movie_title="Movie B",
                    cinema_id="cin-004",
                    cinema_name="Cinema Four",
                    showtime=showtime,
                    external_id="494935",
                    room="New room",
                ),
                command.ScreeningInput(
                    movie_id="mov-003",
                    movie_title="Movie C",
                    cinema_id="cin-004",
                    cinema_name="Cinema Four",
                    showtime=showtime,
                    external_id="unrelated-id",
                ),
            )
        )
    )

    assert result.skipped_count == 1
    assert result.total_count == result.imported_count == 1
    assert result.updated_count == 0
    assert result.screenings[0].movie_title == "Movie C"
    assert await screening_gateway.find_by_id("owner") == owner_before
    assert await screening_gateway.find_by_id("target") == target_before
    target = await screening_gateway.read_import_candidates(
        cinema_id="cin-004",
        movie_id="mov-002",
        showtime=showtime,
        external_id="494935",
    )
    assert len(target) == 1 + int(existing_target)
    unrelated = await screening_gateway.read_import_candidates(
        cinema_id="cin-004",
        movie_id="mov-003",
        showtime=showtime,
        external_id="unrelated-id",
    )
    assert len(unrelated) == 1
    assert unrelated[0]["external_id"] == "unrelated-id"


@pytest.mark.asyncio
@pytest.mark.parametrize("external_id", ["14384", None])
async def test_import_accepts_shared_external_id_across_cinemas(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
    db_pool: asyncpg.Pool,
    external_id: str | None,
) -> None:
    """Different cinemas import shared or absent IDs and reimport without duplicates."""
    await _seed_parents(gateway, movie_gateway)
    command = CreateScreeningsCommand(SupabaseScreeningRepository(screening_gateway))
    reader = SupabaseScreeningReadGateway(db_pool, "marquise-test")
    showtime = datetime(2026, 10, 7, 17, tzinfo=UTC)
    request = command.InputData(
        screenings=(
            command.ScreeningInput(
                movie_id="mov-001",
                movie_title="Movie A",
                cinema_id="cin-001",
                cinema_name="Cinema One",
                showtime=showtime,
                external_id=external_id,
            ),
            command.ScreeningInput(
                movie_id="mov-002",
                movie_title="Movie B",
                cinema_id="cin-004",
                cinema_name="Cinema Four",
                showtime=showtime,
                external_id=external_id,
                room="Old room",
            ),
        )
    )

    result = await command.execute(request)
    assert result.total_count == result.imported_count == 2
    assert result.updated_count == result.skipped_count == 0
    before = await reader.search()

    request = replace(
        request,
        screenings=(
            request.screenings[0],
            replace(request.screenings[1], room="New room"),
        ),
    )
    result = await command.execute(request)
    assert result.total_count == result.updated_count == 2
    assert result.imported_count == result.skipped_count == 0
    after = await reader.search()
    assert after.total == 2
    assert [row["id"] for row in after.rows] == [row["id"] for row in before.rows]
    stored = [await screening_gateway.find_by_id(row["id"]) for row in after.rows]
    assert [row["external_id"] for row in stored] == [external_id, external_id]
    owner_before = next(row for row in before.rows if row["cinema_id"] == "cin-001")
    owner = await reader.search(cinema_id="cin-001")
    assert owner.rows == [owner_before]
    target = await reader.search(cinema_id="cin-004")
    assert target.rows[0]["room"] == "New room"


@pytest.mark.asyncio
async def test_save_does_not_misclassify_primary_key_conflict(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """An unrelated unique violation stays fatal, even when an external ID is set."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 12, 21, tzinfo=UTC)
    await screening_gateway.save(
        screening_id="duplicate-primary-key",
        movie_id="mov-001",
        cinema_id="cin-004",
        showtime=showtime,
    )

    with pytest.raises(asyncpg.UniqueViolationError) as raised:
        await screening_gateway.save(
            screening_id="duplicate-primary-key",
            movie_id="mov-002",
            cinema_id="cin-004",
            showtime=showtime,
            external_id="fresh-id",
        )

    assert raised.value.constraint_name == "screenings_pkey"


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify distinct movies are returned for a cinema within a date range."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-distinct-001",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-distinct-002",
        movie_id="mov-001",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 20, 0, 0, tzinfo=UTC),
    )
    await screening_gateway.save(
        screening_id="scr-distinct-003",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 7, 21, 0, 0, tzinfo=UTC),
    )

    page = await screening_gateway.find_distinct_movies_by_cinema(
        cinema_id="cin-003",
        start_date=datetime(2026, 6, 7, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 8, 23, 59, 59, tzinfo=UTC),
    )

    assert page.total == 2
    assert {row["id"] for row in page.rows} == {"mov-001", "mov-002"}


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema_empty(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify an empty page is returned when no screening matches."""
    page = await screening_gateway.find_distinct_movies_by_cinema(
        cinema_id="cin-empty",
        start_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC),
    )
    assert page.rows == []
    assert page.total == 0


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema_with_limit_and_offset(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify limit/offset paginate distinct movies while total reflects all of them."""
    await _seed_parents(gateway, movie_gateway)
    for movie_id in ("mov-001", "mov-002", "mov-003"):
        await screening_gateway.save(
            screening_id=f"scr-distinct-page-{movie_id}",
            movie_id=movie_id,
            cinema_id="cin-004",
            showtime=datetime(2026, 6, 7, 19, 0, 0, tzinfo=UTC),
        )

    page = await screening_gateway.find_distinct_movies_by_cinema(
        cinema_id="cin-004",
        start_date=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC),
        limit=2,
        offset=1,
    )

    assert page.total == 3
    assert len(page.rows) == 2


@pytest.mark.asyncio
async def test_replace_updates_all_fields_by_id(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify replace writes identity and optional fields for a known ID."""
    await _seed_parents(gateway, movie_gateway)
    await screening_gateway.save(
        screening_id="scr-replace-001",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        ticket_url="https://old.example/t",
        room="Salle 1",
        language="V.F.",
    )

    replaced = await screening_gateway.replace(
        screening_id="scr-replace-001",
        movie_id="mov-002",
        cinema_id="cin-003",
        showtime=datetime(2026, 6, 8, 21, 0, 0, tzinfo=UTC),
        ticket_url=None,
        room="Salle 9",
        language="V.O.",
        fields=frozenset(
            {
                "movie_id",
                "cinema_id",
                "showtime",
                "external_id",
                "ticket_url",
                "room",
                "language",
            }
        ),
    )

    assert replaced is not None
    assert replaced["id"] == "scr-replace-001"
    assert replaced["movie_id"] == "mov-002"
    assert replaced["cinema_id"] == "cin-003"
    assert replaced["ticket_url"] is None
    assert replaced["room"] == "Salle 9"
    assert replaced["language"] == "V.O."

    found = await screening_gateway.find_by_id("scr-replace-001")
    assert found is not None
    assert found["movie__id"] == "mov-002"
    assert found["cinema__id"] == "cin-003"


@pytest.mark.asyncio
async def test_replace_missing_returns_none(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify replace returns None when the screening ID does not exist."""
    result = await screening_gateway.replace(
        screening_id="scr-replace-missing",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 8, 21, 0, 0, tzinfo=UTC),
        fields=frozenset({"movie_id", "cinema_id", "showtime"}),
    )
    assert result is None


@pytest.mark.asyncio
async def test_replace_raises_on_identity_conflict(
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """Verify replace raises GatewayError when identity collides."""
    await _seed_parents(gateway, movie_gateway)
    showtime = datetime(2026, 6, 9, 19, 0, 0, tzinfo=UTC)
    await screening_gateway.save(
        screening_id="scr-replace-conflict-a",
        movie_id="mov-001",
        cinema_id="cin-001",
        showtime=showtime,
    )
    await screening_gateway.save(
        screening_id="scr-replace-conflict-b",
        movie_id="mov-002",
        cinema_id="cin-001",
        showtime=datetime(2026, 6, 10, 19, 0, 0, tzinfo=UTC),
    )

    with pytest.raises(GatewayError):
        await screening_gateway.replace(
            screening_id="scr-replace-conflict-b",
            movie_id="mov-001",
            cinema_id="cin-001",
            showtime=showtime,
            fields=frozenset({"movie_id", "cinema_id", "showtime"}),
        )


@pytest.mark.asyncio
async def test_delete_missing_returns_false(
    screening_gateway: SupabaseScreeningGateway,
) -> None:
    """Verify delete returns false when screening ID does not exist."""
    assert await screening_gateway.delete("scr-delete-missing") is False
