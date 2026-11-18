"""Tests for shared CLI helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from conftest import make_cinema_data, mock_use_case, patch_factory_session
from marquise import ListCinemasUseCase
from marquise_cli.helpers import connected_factory, list_every_cinema


@pytest.mark.asyncio
async def test_connected_factory_closes_the_session_after_a_failure(
    mock_factory: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The factory session closes when the command body raises."""
    session = patch_factory_session(monkeypatch, mock_factory)

    with pytest.raises(RuntimeError, match="boom"):
        async with connected_factory() as factory:
            assert factory is mock_factory
            raise RuntimeError("boom")

    assert session.closed


@pytest.mark.asyncio
async def test_list_every_cinema_reads_pages_until_the_total(
    mock_factory: MagicMock,
) -> None:
    """Two full pages of 100 and a last page of 1 make 201 cinemas."""
    use_case = mock_use_case(ListCinemasUseCase)
    pages = [
        [make_cinema_data(f"cin-{page}-{index}") for index in range(count)]
        for page, count in ((1, 100), (2, 100), (3, 1))
    ]
    use_case.execute.side_effect = [
        ListCinemasUseCase.OutputData(cinemas=page, total=201) for page in pages
    ]
    mock_factory.cinemas.list_cinemas_use_case = use_case

    cinemas = await list_every_cinema(mock_factory, name="Parc")

    assert cinemas == [cinema for page in pages for cinema in page]
    assert use_case.execute.await_args_list == [
        call(ListCinemasUseCase.InputData(page=page, size=100, name="Parc"))
        for page in (1, 2, 3)
    ]


@pytest.mark.asyncio
async def test_list_every_cinema_stops_on_an_empty_page(
    mock_factory: MagicMock,
) -> None:
    """A page with no cinemas ends the walk even if the total is not reached."""
    use_case = mock_use_case(ListCinemasUseCase)
    use_case.execute.return_value = ListCinemasUseCase.OutputData(cinemas=[], total=5)
    mock_factory.cinemas.list_cinemas_use_case = use_case

    assert await list_every_cinema(mock_factory, name=None) == []
    use_case.execute.assert_awaited_once()
