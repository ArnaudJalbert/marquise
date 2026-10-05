"""Tests for SupabaseScreeningRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
    ScreeningNotFoundError,
)
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)
from marquise.interface_adapters.repositories.protocols.base import (
    GatewayError,
    GatewayPage,
)
from marquise.interface_adapters.repositories.protocols.screening import (
    SaveOutcome,
    ScreeningExternalIdConflictGatewayError,
    ScreeningGateway,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide a sample Cinema for tests."""
    return Cinema(
        id=CinemaId(value="cin-789"),
        name="Test Cinema",
    )


@pytest.fixture
def sample_movie() -> Movie:
    """Provide a sample Movie for tests."""
    return Movie(
        id=MovieId(value="mov-456"),
        title="Test Movie",
    )


@pytest.fixture
def sample_screening(sample_cinema: Cinema, sample_movie: Movie) -> Screening:
    """Provide a sample Screening for tests."""
    return Screening(
        id=ScreeningId(value="scr-123"),
        movie=sample_movie,
        cinema=sample_cinema,
        showtime=Showtime(value=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)),
    )


@pytest.fixture
def gateway_dict() -> dict:
    """Provide a sample gateway return dict with joined data.

    The showtime value is a naive datetime to simulate asyncpg's return
    from a ``TIMESTAMP`` column.
    """
    return {
        "id": "scr-123",
        "movie_id": "mov-456",
        "cinema_id": "cin-789",
        "showtime": datetime(2026, 6, 7, 19, 30, 0),
        "external_id": None,
        "ticket_url": None,
        "room": None,
        "language": None,
        "movie__id": "mov-456",
        "movie__title": "Test Movie",
        "movie__release_year": None,
        "movie__directors": None,
        "movie__cast_members": None,
        "movie__duration_minutes": None,
        "movie__description": None,
        "movie__poster_url": None,
        "movie__trailer_url": None,
        "movie__genres": None,
        "movie__original_title": None,
        "movie__rating": None,
        "movie__origin_countries": None,
        "cinema__id": "cin-789",
        "cinema__name": "Test Cinema",
        "cinema__address": None,
        "cinema__city": None,
        "cinema__website": None,
    }


@pytest.mark.asyncio
async def test_save(
    sample_screening: Screening,
    sample_cinema: Cinema,
    sample_movie: Movie,
) -> None:
    """Test save delegates to gateway and maps result."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.save.return_value = SaveOutcome(
        row={
            "id": "scr-123",
            "movie_id": "mov-456",
            "cinema_id": "cin-789",
            "showtime": datetime(2026, 6, 7, 19, 30, 0),
            "external_id": None,
            "ticket_url": None,
            "room": None,
            "language": None,
        },
        inserted=True,
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.save(sample_screening)

    assert result.id == ScreeningId(value="scr-123")
    assert result.movie == sample_movie
    assert result.cinema == sample_cinema
    assert result.showtime.value.tzinfo == UTC
    assert result.showtime.value == datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    assert result.external_id is None
    assert result.ticket_url is None
    assert result.room is None
    assert result.language is None
    mock_gateway.save.assert_awaited_once_with(
        screening_id="scr-123",
        movie_id="mov-456",
        cinema_id="cin-789",
        showtime=datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
        external_id=None,
        ticket_url=None,
        room=None,
        language=None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["save", "update", "replace"])
async def test_translates_external_id_conflict(
    sample_screening: Screening,
    operation: str,
) -> None:
    """Insert/update external-ID conflicts become specific application errors."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    error = ScreeningExternalIdConflictGatewayError(
        "A screening with external_id='486899' already exists"
    )
    getattr(mock_gateway, operation).side_effect = error
    repo = SupabaseScreeningRepository(gateway=mock_gateway)

    with pytest.raises(
        ScreeningExternalIdConflictError, match="external_id='486899'"
    ) as raised:
        if operation == "replace":
            await repo.replace(sample_screening, fields=frozenset({"external_id"}))
        else:
            await getattr(repo, operation)(sample_screening)

    assert raised.value.__cause__ is error
    getattr(mock_gateway, operation).assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["save", "update"])
async def test_unrelated_gateway_error_is_not_a_duplicate(
    sample_screening: Screening,
    operation: str,
) -> None:
    """Unrelated gateway failures propagate instead of triggering duplicate handling."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    error = GatewayError("Database unavailable")
    getattr(mock_gateway, operation).side_effect = error
    repo = SupabaseScreeningRepository(gateway=mock_gateway)

    with pytest.raises(GatewayError, match="Database unavailable") as raised:
        await getattr(repo, operation)(sample_screening)

    assert raised.value is error


@pytest.mark.asyncio
async def test_save_raises_when_row_already_exists(
    sample_screening: Screening,
) -> None:
    """Test save raises error when gateway returns not-inserted."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.save.return_value = SaveOutcome(
        row={
            "id": "scr-123",
            "movie_id": "mov-456",
            "cinema_id": "cin-789",
            "showtime": datetime(2026, 6, 7, 19, 30, 0),
            "external_id": None,
            "ticket_url": None,
            "room": None,
            "language": None,
        },
        inserted=False,
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)

    with pytest.raises(ScreeningAlreadyExistsError):
        await repo.save(sample_screening)


@pytest.mark.asyncio
async def test_find_by_id(gateway_dict: dict) -> None:
    """Test find_by_id returns entity when found."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_by_id.return_value = gateway_dict

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.find_by_id(ScreeningId(value="scr-123"))

    assert result is not None
    assert result.id == ScreeningId(value="scr-123")
    assert result.movie.id == MovieId(value="mov-456")
    assert result.showtime.value.tzinfo == UTC
    assert result.showtime.value == datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC)
    mock_gateway.find_by_id.assert_awaited_once_with(screening_id="scr-123")


@pytest.mark.asyncio
async def test_save_with_timezone_aware_datetime(
    sample_screening: Screening,
) -> None:
    """Test save handles gateway returning timezone-aware datetime."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.save.return_value = SaveOutcome(
        row={
            "id": "scr-123",
            "movie_id": "mov-456",
            "cinema_id": "cin-789",
            "showtime": datetime(2026, 6, 7, 19, 30, 0, tzinfo=UTC),
            "external_id": None,
            "ticket_url": None,
            "room": None,
            "language": None,
        },
        inserted=True,
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.save(sample_screening)

    assert result.showtime.value.tzinfo == UTC


@pytest.mark.asyncio
async def test_find_by_id_missing() -> None:
    """Test find_by_id raises ScreeningNotFoundError when not found."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_by_id.return_value = None

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    with pytest.raises(ScreeningNotFoundError):
        await repo.find_by_id(ScreeningId(value="scr-999"))


@pytest.mark.asyncio
async def test_to_entity_populates_release_year() -> None:
    """Test _to_entity populates release_year from gateway data."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    raw = {
        "id": "scr-456",
        "movie_id": "mov-456",
        "cinema_id": "cin-789",
        "showtime": datetime(2026, 7, 1, 14, 0, 0),
        "external_id": None,
        "ticket_url": None,
        "room": None,
        "language": None,
        "movie__id": "mov-456",
        "movie__title": "Test Movie",
        "movie__release_year": 2026,
        "movie__directors": None,
        "movie__cast_members": None,
        "movie__duration_minutes": None,
        "movie__description": None,
        "movie__poster_url": None,
        "movie__trailer_url": None,
        "movie__genres": None,
        "movie__original_title": None,
        "movie__rating": None,
        "movie__origin_countries": None,
        "cinema__id": "cin-789",
        "cinema__name": "Test Cinema",
        "cinema__address": None,
        "cinema__city": None,
        "cinema__website": None,
    }
    mock_gateway.find_by_id.return_value = raw

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.find_by_id(ScreeningId(value="scr-456"))

    assert result is not None
    assert result.movie.release_year == 2026


@pytest.mark.asyncio
async def test_search_with_all_filters(gateway_dict: dict) -> None:
    """Test search converts value objects to strings and maps the result."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.search.return_value = GatewayPage(rows=[gateway_dict], total=1)

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    start = datetime(2026, 6, 7, tzinfo=UTC)
    end = datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC)
    result = await repo.search(
        movie_id=MovieId(value="mov-456"),
        movie_title="Test",
        cinema_id=CinemaId(value="cin-789"),
        start_date=start,
        end_date=end,
        language="V.O.",
        limit=10,
        offset=0,
    )

    assert len(result.items) == 1
    assert result.total == 1
    mock_gateway.search.assert_awaited_once_with(
        movie_id="mov-456",
        movie_title="Test",
        cinema_id="cin-789",
        start_date=start,
        end_date=end,
        language="V.O.",
        limit=10,
        offset=0,
    )


@pytest.mark.asyncio
async def test_search_with_no_filters(gateway_dict: dict) -> None:
    """Test search passes None through for every omitted filter."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.search.return_value = GatewayPage(rows=[gateway_dict], total=1)

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    await repo.search()

    mock_gateway.search.assert_awaited_once_with(
        movie_id=None,
        movie_title=None,
        cinema_id=None,
        start_date=None,
        end_date=None,
        language=None,
        limit=None,
        offset=0,
    )


@pytest.mark.asyncio
async def test_search_empty() -> None:
    """Test search returns an empty page."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.search.return_value = GatewayPage(rows=[], total=0)

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.search(movie_title="nonexistent")

    assert result.items == []
    assert result.total == 0


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema() -> None:
    """Test find_distinct_movies_by_cinema maps rows to Movie entities."""
    movie_row = {
        "id": "mov-456",
        "title": "Test Movie",
        "release_year": 2026,
        "directors": None,
        "cast_members": None,
        "duration_minutes": None,
        "description": None,
        "poster_url": None,
        "trailer_url": None,
        "genres": None,
        "original_title": None,
        "rating": None,
        "origin_countries": None,
    }
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_distinct_movies_by_cinema.return_value = GatewayPage(
        rows=[movie_row], total=1
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    start = datetime(2026, 6, 7, tzinfo=UTC)
    end = datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC)
    result = await repo.find_distinct_movies_by_cinema(
        cinema_id=CinemaId(value="cin-789"),
        start_date=start,
        end_date=end,
    )

    assert len(result.items) == 1
    assert result.total == 1
    assert result.items[0].id == MovieId(value="mov-456")
    assert result.items[0].title == "Test Movie"
    assert result.items[0].release_year == 2026
    mock_gateway.find_distinct_movies_by_cinema.assert_awaited_once_with(
        cinema_id="cin-789",
        start_date=start,
        end_date=end,
        limit=None,
        offset=0,
    )


@pytest.mark.asyncio
async def test_find_distinct_movies_by_cinema_empty() -> None:
    """Test find_distinct_movies_by_cinema returns an empty page."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.find_distinct_movies_by_cinema.return_value = GatewayPage(
        rows=[], total=0
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.find_distinct_movies_by_cinema(
        cinema_id=CinemaId(value="cin-empty"),
        start_date=datetime(2026, 6, 7, tzinfo=UTC),
        end_date=datetime(2026, 6, 7, 23, 59, 59, tzinfo=UTC),
    )

    assert result.items == []
    assert result.total == 0


@pytest.mark.asyncio
async def test_replace(
    sample_screening: Screening,
    sample_cinema: Cinema,
    sample_movie: Movie,
    gateway_dict: dict,
) -> None:
    """Test replace delegates to the gateway and maps the result."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.replace.return_value = {
        **gateway_dict,
        "id": "scr-123",
        "movie_id": "mov-456",
        "cinema_id": "cin-789",
        "showtime": datetime(2026, 6, 8, 21, 0, 0),
        "external_id": None,
        "ticket_url": "https://tickets.example/1",
        "room": "Salle 4",
        "language": "V.O.",
    }
    updated = Screening(
        id=sample_screening.id,
        movie=sample_movie,
        cinema=sample_cinema,
        showtime=Showtime(value=datetime(2026, 6, 8, 21, 0, 0, tzinfo=UTC)),
        ticket_url="https://tickets.example/1",
        room="Salle 4",
        language="V.O.",
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    fields = frozenset(
        {
            "movie_id",
            "cinema_id",
            "showtime",
            "external_id",
            "ticket_url",
            "room",
            "language",
        }
    )
    result = await repo.replace(updated, fields=fields)

    assert result.id == ScreeningId(value="scr-123")
    assert result.movie == sample_movie
    assert result.cinema == sample_cinema
    assert result.showtime.value == datetime(2026, 6, 8, 21, 0, 0, tzinfo=UTC)
    assert result.ticket_url == "https://tickets.example/1"
    mock_gateway.replace.assert_awaited_once_with(
        screening_id="scr-123",
        movie_id="mov-456",
        cinema_id="cin-789",
        showtime=datetime(2026, 6, 8, 21, 0, 0, tzinfo=UTC),
        external_id=None,
        ticket_url="https://tickets.example/1",
        room="Salle 4",
        language="V.O.",
        fields=fields,
    )


@pytest.mark.asyncio
async def test_replace_raises_not_found(sample_screening: Screening) -> None:
    """Test replace raises ScreeningNotFoundError when the gateway misses."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.replace.return_value = None

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    with pytest.raises(ScreeningNotFoundError, match="scr-123"):
        await repo.replace(sample_screening, fields=frozenset({"room"}))


@pytest.mark.asyncio
async def test_replace_raises_already_exists_on_gateway_error(
    sample_screening: Screening,
) -> None:
    """Test replace translates a unique-constraint GatewayError."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.replace.side_effect = GatewayError("already exists")

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    with pytest.raises(ScreeningAlreadyExistsError, match="already exists"):
        await repo.replace(
            sample_screening, fields=frozenset({"movie_id", "cinema_id", "showtime"})
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("fields", [frozenset(), frozenset({"room"})])
async def test_replace_preserves_mask_and_maps_current_parents(
    sample_screening: Screening, gateway_dict: dict, fields: frozenset[str]
) -> None:
    """A partial write returns actual stored parents, not the request's snapshot."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.replace.return_value = {
        **gateway_dict,
        "movie_id": "mov-concurrent",
        "movie__id": "mov-concurrent",
        "movie__title": "Concurrent Movie",
        "movie__release_year": 2026,
        "cinema_id": "cin-concurrent",
        "cinema__id": "cin-concurrent",
        "cinema__name": "Concurrent Cinema",
        "room": None,
    }
    repo = SupabaseScreeningRepository(gateway=mock_gateway)

    result = await repo.replace(sample_screening, fields=fields)

    assert str(result.movie.id) == "mov-concurrent"
    assert result.movie.title == "Concurrent Movie"
    assert result.movie.release_year == 2026
    assert str(result.cinema.id) == "cin-concurrent"
    assert result.cinema.name == "Concurrent Cinema"
    assert result.room is None
    assert mock_gateway.replace.await_args.kwargs["fields"] == fields
    mock_gateway.replace.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_delegates_to_gateway() -> None:
    """Test delete delegates to gateway and returns None on success."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.delete.return_value = None

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    result = await repo.delete(ScreeningId(value="scr-123"))

    assert result is None
    mock_gateway.delete.assert_awaited_once_with(screening_id="scr-123")


@pytest.mark.asyncio
async def test_delete_missing_raises_not_found() -> None:
    """Test delete translates gateway miss into ScreeningNotFoundError."""
    mock_gateway = create_autospec(ScreeningGateway, instance=True)
    mock_gateway.delete.side_effect = GatewayError(
        "A screening with ID 'scr-missing' was not found"
    )

    repo = SupabaseScreeningRepository(gateway=mock_gateway)
    with pytest.raises(ScreeningNotFoundError, match="scr-missing"):
        await repo.delete(ScreeningId(value="scr-missing"))
