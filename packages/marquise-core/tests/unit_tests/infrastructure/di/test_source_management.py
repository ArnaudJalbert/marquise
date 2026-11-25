"""Tests for source-management DI wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.infrastructure.di.source_management import (
    build_assign_source_use_case,
    build_create_source_use_case,
    build_delete_source_use_case,
    build_get_cinema_source_use_case,
    build_unassign_source_use_case,
)


def test_source_definition_builders_use_supplied_pool_and_schema() -> None:
    """Source definition use cases share explicit pool and schema inputs."""
    pool = MagicMock()

    use_cases = (
        build_create_source_use_case(pool, "test_schema"),
        build_delete_source_use_case(pool, "test_schema"),
    )

    assert isinstance(use_cases[0], CreateSourceUseCase)
    assert isinstance(use_cases[1], DeleteSourceUseCase)
    for use_case in use_cases:
        gateway = use_case.source_repository._gateway
        assert gateway._pool is pool
        assert gateway._table == '"test_schema".source_definitions'
    pool.acquire.assert_not_called()


def test_assignment_builders_wire_explicit_collaborators() -> None:
    """Assignment use cases receive supplied cinema repository, pool, and schema."""
    pool = MagicMock()
    cinema_repository = create_autospec(CinemaRepository, instance=True)

    assign = build_assign_source_use_case(pool, "test_schema", cinema_repository)
    unassign = build_unassign_source_use_case(pool, "test_schema")
    get_source = build_get_cinema_source_use_case(pool, "test_schema")

    assert isinstance(assign, AssignSourceUseCase)
    assert isinstance(unassign, UnassignSourceUseCase)
    assert isinstance(get_source, GetCinemaSourceUseCase)
    assert assign.cinema_repository is cinema_repository
    assert assign.source_definition_repository._gateway._pool is pool
    for use_case in (assign, unassign, get_source):
        assert use_case.assignment_repository._gateway._pool is pool
        assert use_case.assignment_repository._gateway._schema == "test_schema"
    pool.acquire.assert_not_called()
