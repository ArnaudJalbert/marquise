# Use case structure

Read when deciding what a use case does and how its class is laid out.

## Responsibility

- A use case does one job. If two steps need different failure behaviour, split them into two use cases.
- A coordinating use case's only job is to call use cases one after the other, optionally reformatting data to pass to the next one. It holds no business logic.
- A coordinating use case has no loops or conditions. If it needs one, the logic belongs in the use cases it calls. A comprehension that only reshapes data to pass along counts as reformatting.
- Every other use case receives no use cases as dependencies.
- A command returns as little as possible, such as the IDs it created. Returning data is a query's job.
- A use case that acts on data another command created fetches that data itself through a query. To work on a specific set, it receives their IDs.

```python
class ImportCinemaCommand:
    """Fetch a cinema's titles, then add their movies."""

    def __init__(
        self,
        fetch_titles: FetchTitlesQuery,
        add_movies: AddCinemaMoviesCommand,
    ) -> None:
        self._fetch_titles = fetch_titles
        self._add_movies = add_movies

    async def execute(self, input_data: InputData) -> OutputData:
        """Import the movies a cinema shows.

        Args:
            input_data: The cinema to import.

        Returns:
            The ID of each imported movie.
        """
        fetch_request = self._fetch_titles.InputData(input_data.cinema_id)
        fetched = await self._fetch_titles.execute(fetch_request)
        add_request = self._add_movies.InputData(input_data.cinema_id, fetched.titles)
        added = await self._add_movies.execute(add_request)
        return self.OutputData(movie_ids=added.movie_ids)
```

## Layout

- All of a use case's logic lives in its class. Never put a function outside the class: a helper that doesn't need `self` is a private static method. It may call methods on domain entities and value objects, because rules that are true of an entity everywhere stay on the entity.
- `execute(input_data: InputData) -> OutputData` is the only public member. All other methods and stored dependencies are private. `InputData` and `OutputData` stay public because callers need them, and so do the input classes nested in `InputData`, such as one `MovieInput` per movie. Use those input classes to shape input data. Never use a dict for it.
- `execute` always has a complete Google-style docstring, because it is the only public method: a summary, then `Args`, `Returns` and every exception it raises itself under `Raises`.
- `execute` reads as a short list of named steps. Each private method calls the next level down and sits right below its caller, so the file reads from top to bottom.
- Functions follow [functions](../functions.md).

```python
# Prohibited: a function outside the class.
def _normalize_title(title: str) -> str:
    return " ".join(title.split())


class AddCinemaMoviesCommand:
    ...


# Mandatory: a private static method.
class AddCinemaMoviesCommand:
    @staticmethod
    def _normalize_title(title: str) -> str:
        return " ".join(title.split())
```

```text
execute
├── _require_cinema
├── _match_titles
│   └── _find_tmdb_id
├── _find_stored_movies
└── _create_missing_movies
    ├── _create_matched_movie
    └── _create_unmatched_movie
```

`execute` reads as named steps, and each method sits right below its caller:

```python
async def execute(self, input_data: InputData) -> OutputData:
    """..."""
    await self._require_cinema(input_data.cinema_id)
    matches = await self._match_titles(input_data.titles)
    stored_movies = await self._find_stored_movies(matches.matched)
    created_movies = await self._create_missing_movies(matches, stored_movies)
    movies = [*stored_movies, *created_movies]
    logger.info("Added %d movies for %s", len(movies), input_data.cinema_id)
    return self.OutputData(movie_ids=tuple(movie.id.value for movie in movies))

async def _require_cinema(self, cinema_id: str) -> None:
    ...

async def _match_titles(self, titles: tuple[str, ...]) -> TitleMatches:
    tmdb_ids = [await self._find_tmdb_id(title) for title in titles]
    ...

async def _find_tmdb_id(self, title: str) -> str | None:
    ...

async def _find_stored_movies(self, matched: tuple[MatchedTitle, ...]) -> list[Movie]:
    ...
```
