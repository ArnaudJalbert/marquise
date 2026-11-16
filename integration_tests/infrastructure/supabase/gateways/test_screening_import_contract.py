"""PostgreSQL conformance to the policy-free import persistence contract."""

from collections.abc import Awaitable, Callable

import pytest
import pytest_asyncio

from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Screening
from marquise.infrastructure.supabase.gateways.cinema import SupabaseCinemaGateway
from marquise.infrastructure.supabase.gateways.movie import SupabaseMovieGateway
from marquise.infrastructure.supabase.gateways.screening import SupabaseScreeningGateway
from marquise.infrastructure.supabase.gateways.source_definition import (
    SupabaseSourceDefinitionGateway,
)
from marquise.interface_adapters.repositories.supabase.screening_repository import (
    SupabaseScreeningRepository,
)
from support.screening_contract import (
    assert_checked_writes,
    assert_removed_owner,
    assert_target_arrival,
)
from support.screening_import import owner


@pytest_asyncio.fixture
async def contract_source(
    source_definition_gateway: SupabaseSourceDefinitionGateway,
) -> None:
    """Persist the source referenced by the shared import contract."""
    await source_definition_gateway.save("cineplex", "Cineplex")


@pytest.mark.usefixtures("contract_source")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario", [assert_checked_writes, assert_target_arrival, assert_removed_owner]
)
async def test_postgres_checked_write_contract(
    scenario: Callable[[ScreeningRepository, Screening], Awaitable[None]],
    screening_gateway: SupabaseScreeningGateway,
    gateway: SupabaseCinemaGateway,
    movie_gateway: SupabaseMovieGateway,
) -> None:
    """PostgreSQL detects stale snapshots and arrivals without policy predicates."""
    await gateway.save("cin", "Cinema", address=None, city=None)
    await movie_gateway.save("movie", "Film", release_year=None)
    await scenario(SupabaseScreeningRepository(screening_gateway), owner())
