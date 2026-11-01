"""Tests for ListMoviesUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import TooManyMovieIdsError
from marquise.application.repositories import MovieRepository, Page
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


@pytest.mark.asyncio
async def test_list_movies_returns_all_when_no_filter() -> None:
    """Verify all movies are returned when no title filter is provided."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[
            Movie(id=MovieId(value="id-1"), title="Movie A"),
            Movie(id=MovieId(value="id-2"), title="Movie B"),
        ],
        total=2,
    )

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData()

    response = await use_case.execute(request)

    assert len(response.movies) == 2
    assert response.movies[0].id == "id-1"
    assert response.movies[0].title == "Movie A"
    assert response.movies[1].id == "id-2"
    assert response.movies[1].title == "Movie B"
    assert response.total == 2
    mock_repo.find_all.assert_awaited_once_with(title_filter=None, limit=None, offset=0)


@pytest.mark.asyncio
async def test_list_movies_passes_page_and_size_as_limit_offset() -> None:
    """Verify page/size are converted to limit/offset for the repository.

    Page 2, size 5 should produce limit=5, offset=5.
    """
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_all.return_value = Page(items=[], total=50)

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData(page=2, size=5)

    await use_case.execute(request)

    mock_repo.find_all.assert_awaited_once_with(title_filter=None, limit=5, offset=5)


@pytest.mark.asyncio
async def test_list_movies_passes_none_size_as_unbounded() -> None:
    """Verify size=None passes limit=None, offset=0 (unbounded)."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_all.return_value = Page(items=[], total=50)

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData(page=1, size=None)

    await use_case.execute(request)

    mock_repo.find_all.assert_awaited_once_with(title_filter=None, limit=None, offset=0)


@pytest.mark.asyncio
async def test_list_movies_filters_by_title() -> None:
    """Verify movies are filtered when a title filter is provided."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[Movie(id=MovieId(value="id-1"), title="Movie A")],
        total=1,
    )

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData(title="Movie A")

    response = await use_case.execute(request)

    assert len(response.movies) == 1
    assert response.movies[0].title == "Movie A"
    mock_repo.find_all.assert_awaited_once_with(
        title_filter="Movie A", limit=None, offset=0
    )


@pytest.mark.asyncio
async def test_list_movies_returns_empty_list_when_no_matches() -> None:
    """Verify an empty list is returned when no movies match the filter."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_all.return_value = Page(items=[], total=0)

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData(title="NonExistent")

    response = await use_case.execute(request)

    assert len(response.movies) == 0
    assert response.total == 0
    mock_repo.find_all.assert_awaited_once_with(
        title_filter="NonExistent", limit=None, offset=0
    )


@pytest.mark.asyncio
async def test_list_movies_maps_all_fields_correctly() -> None:
    """Verify all movie fields are mapped to MovieData."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[
            Movie(
                id=MovieId(value="id-1"),
                title="Full Movie",
                release_year=2024,
                directors=("Director A",),
                cast=("Actor A", "Actor B"),
                duration_minutes=120,
                description="A full movie.",
                poster_url="https://example.com/poster.jpg",
                trailer_url="https://example.com/trailer.mp4",
                genres=("Drama", "Comedy"),
                original_title="Le Film Complet",
                rating="13+",
                origin_countries=("Canada",),
                tmdb_rating=8.1,
                tmdb_vote_count=1234,
            ),
        ],
        total=1,
    )

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData()

    response = await use_case.execute(request)

    movie = response.movies[0]
    assert movie.id == "id-1"
    assert movie.title == "Full Movie"
    assert movie.release_year == 2024
    assert movie.directors == ("Director A",)
    assert movie.cast == ("Actor A", "Actor B")
    assert movie.duration_minutes == 120
    assert movie.description == "A full movie."
    assert movie.poster_url == "https://example.com/poster.jpg"
    assert movie.trailer_url == "https://example.com/trailer.mp4"
    assert movie.genres == ("Drama", "Comedy")
    assert movie.original_title == "Le Film Complet"
    assert movie.rating == "13+"
    assert movie.origin_countries == ("Canada",)
    assert movie.tmdb_rating == 8.1 and movie.tmdb_vote_count == 1234


@pytest.mark.asyncio
async def test_list_movies_maps_optional_none_fields() -> None:
    """Verify optional fields are None when the entity has them as None."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[Movie(id=MovieId(value="id-1"), title="Minimal Movie")],
        total=1,
    )

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData()

    response = await use_case.execute(request)

    movie = response.movies[0]
    assert movie.id == "id-1"
    assert movie.title == "Minimal Movie"
    assert movie.release_year is None
    assert movie.directors is None
    assert movie.cast is None
    assert movie.duration_minutes is None
    assert movie.description is None
    assert movie.poster_url is None
    assert movie.trailer_url is None
    assert movie.genres is None
    assert movie.original_title is None
    assert movie.rating is None
    assert movie.origin_countries is None
    assert movie.tmdb_rating is None and movie.tmdb_vote_count is None


@pytest.mark.asyncio
async def test_list_movies_output_total_reflects_repository_total() -> None:
    """The output's total reflects the repository's total, not the page size."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_all.return_value = Page(
        items=[Movie(id=MovieId(value="id-1"), title="Movie A")],
        total=50,
    )

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData(size=1)

    response = await use_case.execute(request)

    assert len(response.movies) == 1
    assert response.total == 50


@pytest.mark.asyncio
async def test_list_movies_rejects_page_below_one() -> None:
    """A page number less than 1 is rejected before the repository is called."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        ListMoviesUseCase.InputData(page=0)


@pytest.mark.asyncio
async def test_list_movies_rejects_zero_or_negative_size() -> None:
    """A non-positive size is rejected before the repository is called."""
    with pytest.raises(ValueError, match="size must be positive when provided"):
        ListMoviesUseCase.InputData(size=0)


@pytest.mark.asyncio
async def test_list_movies_rejects_blank_title() -> None:
    """A whitespace-only title filter is rejected before the repository is called."""
    with pytest.raises(ValueError, match="title must not be empty when provided"):
        ListMoviesUseCase.InputData(title="   ")


@pytest.mark.asyncio
async def test_list_movies_by_ids_returns_matching_movies() -> None:
    """ids mode delegates to find_by_ids and maps results to output data."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_by_ids.return_value = [
        Movie(id=MovieId(value="mov-1"), title="The Odyssey"),
        Movie(id=MovieId(value="mov-2"), title="Sunrise"),
    ]

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData(ids=("mov-1", "mov-2"), size=2)

    response = await use_case.execute(request)

    assert [m.id for m in response.movies] == ["mov-1", "mov-2"]
    assert response.total == 2
    mock_repo.find_by_ids.assert_awaited_once_with(
        [MovieId(value="mov-1"), MovieId(value="mov-2")]
    )
    mock_repo.find_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_movies_by_ids_omits_missing_ids() -> None:
    """IDs with no matching movie are silently omitted, not an error."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_by_ids.return_value = [
        Movie(id=MovieId(value="mov-1"), title="The Odyssey"),
    ]

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData(ids=("mov-1", "missing"), size=2)

    response = await use_case.execute(request)

    assert [m.id for m in response.movies] == ["mov-1"]
    assert response.total == 1


@pytest.mark.asyncio
async def test_list_movies_by_ids_and_title_applies_and_filter() -> None:
    """Combining ids and title filters the ids results by title (AND)."""
    mock_repo = create_autospec(MovieRepository, instance=True)
    mock_repo.find_by_ids.return_value = [
        Movie(id=MovieId(value="mov-1"), title="Dune Part Two"),
        Movie(id=MovieId(value="mov-2"), title="Sunrise"),
    ]

    use_case = ListMoviesUseCase(movie_repository=mock_repo)
    request = ListMoviesUseCase.InputData(ids=("mov-1", "mov-2"), title="dune", size=2)

    response = await use_case.execute(request)

    assert [m.id for m in response.movies] == ["mov-1"]
    assert response.total == 1
    mock_repo.find_all.assert_not_awaited()


def test_list_movies_rejects_empty_ids() -> None:
    """An empty ids tuple is rejected when explicitly provided."""
    with pytest.raises(ValueError, match="ids must not be empty when provided"):
        ListMoviesUseCase.InputData(ids=())


def test_list_movies_rejects_too_many_ids() -> None:
    """More than MAX_MOVIE_IDS ids is rejected."""
    too_many = tuple(f"mov-{i}" for i in range(101))
    with pytest.raises(TooManyMovieIdsError):
        ListMoviesUseCase.InputData(ids=too_many, size=101)


def test_list_movies_rejects_ids_count_exceeding_size() -> None:
    """The number of ids must not exceed the requested page size."""
    with pytest.raises(ValueError, match="ids count must not exceed size"):
        ListMoviesUseCase.InputData(ids=("mov-1", "mov-2"), size=1)


def test_list_movies_rejects_ids_with_page_other_than_one() -> None:
    """ids mode only makes sense on page 1, since everything fits in one page."""
    with pytest.raises(ValueError, match="page must be 1 when ids is provided"):
        ListMoviesUseCase.InputData(ids=("mov-1",), size=1, page=2)
