# Use case testing

Read when writing or reviewing use case tests. General test rules are in [testing](../testing.md).

- Test a use case only through `execute`. Never call its private methods, so they can be reshaped without touching tests.
- Mock every dependency with `create_autospec(Interface, instance=True)`, and mock the data it returns. A use case test uses nothing real.
- A step a test doesn't exercise gets a mock that does nothing, not an optional parameter.
- Assert on what the caller sees: the output, the exception raised, and what was passed to a dependency that changes state.

```python
def _command(
    title_matcher: TitleMatcher,
) -> tuple[AddCinemaMoviesCommand, MovieRepository]:
    cinema_repository = create_autospec(CinemaRepository, instance=True)
    cinema_repository.find_by_id.return_value = Cinema(
        id=CinemaId("cinema-1"), name="Cinema"
    )
    movie_repository = create_autospec(MovieRepository, instance=True)
    movie_repository.create_or_reuse.side_effect = lambda movie: movie
    command = AddCinemaMoviesCommand(cinema_repository, movie_repository, title_matcher)
    return command, movie_repository


@pytest.mark.asyncio
async def test_unmatched_title_creates_movie_without_tmdb_id() -> None:
    """A title with no TMDB match still gets a movie."""
    title_matcher = create_autospec(TitleMatcher, instance=True)
    title_matcher.find_tmdb_id.return_value = None
    command, movie_repository = _command(title_matcher)

    result = await command.execute(command.InputData("cinema-1", ("Unknown",)))

    assert len(result.movie_ids) == 1
    saved_movie = movie_repository.create_or_reuse.await_args.args[0]
    assert saved_movie.title == "Unknown"
    assert saved_movie.tmdb_id is None


@pytest.mark.asyncio
async def test_matcher_failure_stops_before_creating_a_movie() -> None:
    """A TMDB outage raises instead of creating the movie by title alone."""
    title_matcher = create_autospec(TitleMatcher, instance=True)
    title_matcher.find_tmdb_id.side_effect = ConnectionError("offline")
    command, movie_repository = _command(title_matcher)

    with pytest.raises(ConnectionError):
        await command.execute(command.InputData("cinema-1", ("Unknown",)))

    movie_repository.create_or_reuse.assert_not_awaited()
```
