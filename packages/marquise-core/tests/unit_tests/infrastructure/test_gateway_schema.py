"""Contract tests: Postgres gateways and readers take the schema from DI."""

from __future__ import annotations

import inspect

import pytest

from marquise.infrastructure.postgres.gateways.cinema import PostgresCinemaGateway
from marquise.infrastructure.postgres.gateways.cinema_source_assignment import (
    PostgresCinemaSourceAssignmentGateway,
)
from marquise.infrastructure.postgres.gateways.movie import PostgresMovieGateway
from marquise.infrastructure.postgres.gateways.movie_merge import (
    PostgresMovieMergeGateway,
)
from marquise.infrastructure.postgres.gateways.movie_metadata import (
    PostgresMovieMetadataGateway,
)
from marquise.infrastructure.postgres.gateways.screening import (
    PostgresScreeningGateway,
)
from marquise.infrastructure.postgres.gateways.screening_movie_reader import (
    PostgresScreeningMovieReadGateway,
)
from marquise.infrastructure.postgres.gateways.screening_reader import (
    PostgresScreeningReadGateway,
)
from marquise.infrastructure.postgres.gateways.source_definition import (
    PostgresSourceDefinitionGateway,
)
from marquise.interface_adapters.readers.cinema_source_assignment_reader import (
    PostgresCinemaSourceAssignmentReader,
)


@pytest.mark.parametrize(
    "schema_bound_class",
    [
        PostgresCinemaGateway,
        PostgresCinemaSourceAssignmentGateway,
        PostgresMovieGateway,
        PostgresMovieMergeGateway,
        PostgresMovieMetadataGateway,
        PostgresScreeningGateway,
        PostgresScreeningMovieReadGateway,
        PostgresScreeningReadGateway,
        PostgresSourceDefinitionGateway,
        PostgresCinemaSourceAssignmentReader,
    ],
)
def test_schema_has_no_default(schema_bound_class: type) -> None:
    """Scenario: building a gateway or reader without a schema is impossible.

    Given a Postgres gateway or reader class, when its constructor is
    inspected, then ``schema`` is required so only ``settings.schema`` from DI
    can choose it.
    """
    schema = inspect.signature(schema_bound_class).parameters["schema"]

    assert schema.default is inspect.Parameter.empty
