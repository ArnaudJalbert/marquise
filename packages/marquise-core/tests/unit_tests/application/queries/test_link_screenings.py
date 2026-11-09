"""Linking each fetched screening to its stored movie."""

import pytest

from marquise.application.exceptions.movie import MovieNotLinkedError
from marquise.application.queries.link_screenings import LinkScreeningsQuery

ScreeningInput = LinkScreeningsQuery.ScreeningInput
MovieInput = LinkScreeningsQuery.MovieInput


@pytest.fixture
def query() -> LinkScreeningsQuery:
    """The query has no dependencies."""
    return LinkScreeningsQuery()


@pytest.mark.asyncio
async def test_links_ignoring_case_and_spacing(query: LinkScreeningsQuery) -> None:
    """Sources vary title case and spacing, so those differences are ignored."""
    output = await query.execute(
        query.InputData(
            (ScreeningInput("  dune  part two"),),
            (MovieInput("Dune Part Two", "movie-1"),),
        )
    )

    assert output.movie_ids == ("movie-1",)


@pytest.mark.asyncio
async def test_source_identifiers_keep_same_titles_apart(
    query: LinkScreeningsQuery,
) -> None:
    """Two films with one title link by their source identifiers."""
    output = await query.execute(
        query.InputData(
            (ScreeningInput("Same", "two"), ScreeningInput("Same", "one")),
            (
                MovieInput("Same", "movie-1", "one"),
                MovieInput("Same", "movie-2", "two"),
            ),
        )
    )

    assert output.movie_ids == ("movie-2", "movie-1")


@pytest.mark.asyncio
async def test_screening_without_a_movie_raises(query: LinkScreeningsQuery) -> None:
    """A screening must never be saved without its movie."""
    with pytest.raises(MovieNotLinkedError, match="Missing"):
        await query.execute(
            query.InputData(
                (ScreeningInput("Missing"),), (MovieInput("Other", "movie-1"),)
            )
        )


@pytest.mark.parametrize(
    "build",
    [
        lambda: ScreeningInput(1),
        lambda: ScreeningInput("Film", 1),
        lambda: MovieInput("Film", 1),
        lambda: MovieInput(1, "movie-1"),
        lambda: LinkScreeningsQuery.InputData([], ()),
        lambda: LinkScreeningsQuery.InputData((), ("movie",)),
    ],
)
def test_input_rejects_wrong_types(build: object) -> None:
    """Input is the one place types are checked."""
    with pytest.raises(TypeError):
        build()
