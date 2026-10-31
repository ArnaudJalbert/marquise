"""Title variants seen in real imports reuse one movie instead of duplicating it."""

from unittest.mock import create_autospec

import pytest

from marquise.application.metadata import ProviderIdentity
from marquise.application.movie_workflows import (
    MatchMovieExecutor,
    MatchMovieOutputData,
)
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


def _command(
    existing: list[Movie], *results: MatchMovieOutputData
) -> tuple[CreateMissingMoviesCommand, MovieRepository]:
    repo = create_autospec(MovieRepository, instance=True)
    repo.find_by_tmdb_id.return_value = None
    repo.find_by_titles.return_value = existing
    repo.create_or_reuse.side_effect = lambda movie: movie
    matcher = create_autospec(MatchMovieExecutor, instance=True)
    matcher.execute.side_effect = list(results)
    return CreateMissingMoviesCommand(repo, matcher=matcher), repo


async def _import(command: CreateMissingMoviesCommand, *titles: str) -> list[str]:
    output = await command.execute(
        command.InputData(
            movies=tuple(command.MovieInput(title=title) for title in titles)
        )
    )
    return [movie.id for movie in output.movies]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stored", "source"),
    [
        ("Gentle Monster", "Gentle Monster (VOSTA)"),
        ("SUSPIRIA", "Suspiria"),
        ("Godzilla Minus Zero", "GODZILLA MINUS ZERO"),
        ("The Shining", "THE SHINING (anglais avec s.t.f.)"),
        ("Spider-Man: Brand New Day", "SPIDER MAN BRAND NEW DAY"),
        ("Street Fighter", "Street Fighter : le film (version française)"),
    ],
)
async def test_unmatched_variant_reuses_the_stored_movie(
    stored: str, source: str
) -> None:
    """Case, labels and a contained title all resolve to the stored film."""
    command, repo = _command(
        [Movie(id=MovieId("kept"), title=stored, tmdb_id="1")],
        MatchMovieOutputData("incomplete"),
    )

    assert await _import(command, source) == ["kept"]
    repo.create_or_reuse.assert_not_awaited()


@pytest.mark.asyncio
async def test_matched_french_title_adopts_the_stored_english_title() -> None:
    """The matched provider titles find a movie stored under its English title."""
    command, repo = _command(
        [Movie(id=MovieId("english"), title="SPIDER MAN BRAND NEW DAY")],
        MatchMovieOutputData(
            "matched",
            ProviderIdentity("tmdb", "969681"),
            titles=("Spider-Man: Brand New Day",),
            release_year=2026,
        ),
    )

    assert await _import(command, "Spider-Man : Un jour nouveau") == ["english"]
    repo.create_or_reuse.assert_not_awaited()


@pytest.mark.asyncio
async def test_label_variants_in_one_import_share_the_matched_movie() -> None:
    """An unmatched label variant joins its matched sibling, creating one row."""
    command, repo = _command(
        [],
        MatchMovieOutputData(
            "matched", ProviderIdentity("tmdb", "1401459"), titles=("Fjord",)
        ),
        MatchMovieOutputData("incomplete"),
    )

    ids = await _import(command, "Fjord", "Fjord (Multilingual w/e.s.t.)")

    assert len(ids) == 2 and len(set(ids)) == 1
    repo.create_or_reuse.assert_awaited_once()
    assert repo.create_or_reuse.call_args.args[0].tmdb_id == "1401459"


@pytest.mark.asyncio
async def test_same_title_different_film_is_kept_apart_by_year() -> None:
    """A classic and its remake coexist instead of aborting the import."""
    command, repo = _command(
        [Movie(id=MovieId("remake"), title="Sense and Sensibility", tmdb_id="2026")],
        MatchMovieOutputData(
            "matched",
            ProviderIdentity("tmdb", "4584"),
            titles=("Sense and Sensibility",),
            release_year=1995,
        ),
    )

    ids = await _import(command, "SENSE AND SENSIBILITY")

    created = repo.create_or_reuse.call_args.args[0]
    assert ids != ["remake"]
    assert (created.title, created.tmdb_id) == ("SENSE AND SENSIBILITY (1995)", "4584")


@pytest.mark.asyncio
async def test_ambiguous_containment_creates_a_new_movie() -> None:
    """A title contained in two stored films is not guessed."""
    command, repo = _command(
        [
            Movie(id=MovieId("one"), title="Heated Rivalry - Episodes 1 & 2"),
            Movie(id=MovieId("two"), title="Heated Rivalry - Episodes 3 & 4"),
        ],
        MatchMovieOutputData("unmatched"),
    )

    assert await _import(command, "Heated Rivalry") not in (["one"], ["two"])
    repo.create_or_reuse.assert_awaited_once()


@pytest.mark.asyncio
async def test_short_contained_title_does_not_absorb_another_film() -> None:
    """A one-word title under six characters needs an exact key match."""
    command, repo = _command(
        [Movie(id=MovieId("aftershock"), title="Shock Wave")],
        MatchMovieOutputData("unmatched"),
    )

    assert await _import(command, "Shock") != ["aftershock"]
    repo.create_or_reuse.assert_awaited_once()
