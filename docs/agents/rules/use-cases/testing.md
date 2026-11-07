# Use case testing

Read when writing or reviewing use case tests. General test rules are in [testing](../testing.md).

- Test a use case only through `execute`. Never call its private methods, so they can be reshaped without touching tests.
- Mock every dependency with `create_autospec(Interface, instance=True)`, and mock the data it returns. A use case test uses nothing real.
- A step a test doesn't exercise gets a mock that does nothing, not an optional parameter.
- Build the mocks and the use case in pytest fixtures, named as nouns. Each test asks for the fixtures it needs and adjusts only what it is about.
- Assert on what the caller sees: the output, the exception raised, and what was passed to a dependency that changes state.

```python
@pytest.fixture
def cinema_repository() -> CinemaRepository:
    cinema_repository = create_autospec(CinemaRepository, instance=True)
    cinema_repository.find_by_id.return_value = Cinema(
        id=CinemaId("cinema-1"), name="Cinema"
    )
    return cinema_repository


@pytest.fixture
def movie_repository() -> MovieRepository:
    movie_repository = create_autospec(MovieRepository, instance=True)
    movie_repository.find_by_tmdb_id.return_value = None
    movie_repository.create_or_reuse.side_effect = lambda movie: movie
    return movie_repository


@pytest.fixture
def title_matcher() -> TitleMatcher:
    return create_autospec(TitleMatcher, instance=True)


@pytest.fixture
def command(
    cinema_repository: CinemaRepository,
    movie_repository: MovieRepository,
    title_matcher: TitleMatcher,
) -> AddCinemaMoviesCommand:
    return AddCinemaMoviesCommand(cinema_repository, movie_repository, title_matcher)


@pytest.mark.asyncio
async def test_unmatched_title_creates_movie_without_tmdb_id(
    command: AddCinemaMoviesCommand,
    movie_repository: MovieRepository,
    title_matcher: TitleMatcher,
) -> None:
    """A title with no TMDB match still gets a movie."""
    title_matcher.find_tmdb_id.return_value = None

    result = await command.execute(command.InputData("cinema-1", ("Unknown",)))

    assert len(result.movie_ids) == 1
    saved_movie = movie_repository.create_or_reuse.await_args.args[0]
    assert saved_movie.title == "Unknown"
    assert saved_movie.tmdb_id is None


@pytest.mark.asyncio
async def test_matcher_failure_stops_before_creating_a_movie(
    command: AddCinemaMoviesCommand,
    movie_repository: MovieRepository,
    title_matcher: TitleMatcher,
) -> None:
    """A TMDB outage raises instead of creating the movie by title alone."""
    title_matcher.find_tmdb_id.side_effect = ConnectionError("offline")

    with pytest.raises(ConnectionError):
        await command.execute(command.InputData("cinema-1", ("Unknown",)))

    movie_repository.create_or_reuse.assert_not_awaited()
```
