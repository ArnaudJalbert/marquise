"""Tests for GetCinemaScreeningsUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import (
    CinemaRepository,
    Page,
    ScreeningRepository,
)
from marquise.application.use_cases.get_cinema_screenings import (
    GetCinemaScreeningsUseCase,
)
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)


def _input() -> GetCinemaScreeningsUseCase.InputData:
    return GetCinemaScreeningsUseCase.InputData(cinema_id="cin-1")


@pytest.mark.asyncio
async def test_returns_cinema_and_screenings() -> None:
    """The use case returns the cinema with its screenings."""
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    movie = Movie(id=MovieId(value="mov-1"), title="The Odyssey")
    screening = Screening(
        id=ScreeningId(value="scr-1"),
        movie=movie,
        cinema=cinema,
        showtime=Showtime(value=datetime(2026, 6, 27, 19, 30, tzinfo=UTC)),
    )
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.find_by_id.return_value = cinema
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[screening], total=1)

    use_case = GetCinemaScreeningsUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    result = await use_case.execute(_input())

    assert result.cinema_name == "Cinema One"
    assert len(result.screenings) == 1
    assert result.screenings[0].movie_title == "The Odyssey"
    assert result.screenings[0].cinema_id == "cin-1"
    assert result.screenings[0].cinema_name == "Cinema One"
    assert result.screenings[0].showtime.startswith("2026-06-27T19:30")
    assert result.total == 1


@pytest.mark.asyncio
async def test_passes_only_cinema_id_to_repository() -> None:
    """The repository is called with only cinema_id set — no other filters."""
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.find_by_id.return_value = cinema
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[], total=0)

    use_case = GetCinemaScreeningsUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    await use_case.execute(_input())

    screening_repo.search.assert_awaited_once_with(
        cinema_id=CinemaId(value="cin-1"),
        limit=None,
        offset=0,
    )


@pytest.mark.asyncio
async def test_passes_page_and_size_to_repository_as_limit_offset() -> None:
    """page/size from the input are converted to limit/offset for the repository.

    Page 2, size 5 should produce limit=5, offset=5.
    """
    cinema = Cinema(id=CinemaId(value="cin-1"), name="Cinema One")
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.find_by_id.return_value = cinema
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.search.return_value = Page(items=[], total=50)

    use_case = GetCinemaScreeningsUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    request = GetCinemaScreeningsUseCase.InputData(
        cinema_id="cin-1",
        page=2,
        size=5,
    )
    result = await use_case.execute(request)

    screening_repo.search.assert_awaited_once_with(
        cinema_id=CinemaId(value="cin-1"),
        limit=5,
        offset=5,
    )
    assert result.total == 50


def test_input_rejects_page_below_one() -> None:
    """A page less than 1 is rejected."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        GetCinemaScreeningsUseCase.InputData(cinema_id="cin-1", page=0)


def test_input_rejects_non_positive_size() -> None:
    """A non-positive size is rejected when provided."""
    with pytest.raises(ValueError, match="size must be positive when provided"):
        GetCinemaScreeningsUseCase.InputData(cinema_id="cin-1", size=0)


def test_input_rejects_empty_cinema_id() -> None:
    """A whitespace-only cinema_id is rejected."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        GetCinemaScreeningsUseCase.InputData(cinema_id="  ")


@pytest.mark.asyncio
async def test_raises_when_cinema_missing() -> None:
    """A missing cinema raises CinemaNotFoundError before querying screenings."""
    cinema_repo = create_autospec(CinemaRepository, instance=True)
    cinema_repo.find_by_id.return_value = None
    screening_repo = create_autospec(ScreeningRepository, instance=True)

    use_case = GetCinemaScreeningsUseCase(
        cinema_repository=cinema_repo,
        screening_repository=screening_repo,
    )
    with pytest.raises(CinemaNotFoundError):
        await use_case.execute(_input())
    screening_repo.search.assert_not_awaited()
