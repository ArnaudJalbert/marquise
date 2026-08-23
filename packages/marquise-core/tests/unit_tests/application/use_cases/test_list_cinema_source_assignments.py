"""Tests for ListCinemaSourceAssignmentsQuery."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import (
    CinemaSourceAssignmentData,
    CinemaSourceAssignmentReader,
)
from marquise.application.use_cases import ListCinemaSourceAssignmentsQuery


@pytest.mark.asyncio
async def test_list_cinema_source_assignments_returns_reader_data() -> None:
    """Verify query returns every assignment read model unchanged."""
    reader = create_autospec(CinemaSourceAssignmentReader, instance=True)
    expected = [
        CinemaSourceAssignmentData(cinema_id="cin-001", source_display_name="Cineplex")
    ]
    reader.list_all.return_value = expected
    query = ListCinemaSourceAssignmentsQuery(reader)

    response = await query.execute(ListCinemaSourceAssignmentsQuery.InputData())

    assert response.assignments == expected
    reader.list_all.assert_awaited_once()
