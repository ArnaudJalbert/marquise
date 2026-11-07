# Use case structure

Read when deciding what a use case does and how its class is laid out.

## Responsibility

- A use case does one job. If two steps need different failure behaviour, split them into two use cases.
- A coordinating use case's only job is to call use cases one after the other, optionally reformatting data to pass to the next one. It holds no business logic.
- A coordinating use case has no loops or conditions. If it needs one, the logic belongs in the use cases it calls. A comprehension that only reshapes data to pass along counts as reformatting.
- Every other use case receives no use cases as dependencies.

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
- `execute(input_data: InputData) -> OutputData` is the only public member. All other methods and stored dependencies are private. `InputData` and `OutputData` stay public because callers need them.
- `execute` always has a complete Google-style docstring, because it is the only public method: a summary, then `Args`, `Returns` and every exception it raises itself under `Raises`.
- `execute` reads as a short list of named steps. Each private method calls the next level down and sits right below its caller, so the file reads from top to bottom.
- Functions follow [functions](../functions.md).

```python
# Avoid: a function outside the class.
def _normalize_title(title: str) -> str:
    return " ".join(title.split())


class AddCinemaMoviesCommand:
    ...


# Prefer: a private static method.
class AddCinemaMoviesCommand:
    @staticmethod
    def _normalize_title(title: str) -> str:
        return " ".join(title.split())
```

```text
execute
├── _require_cinema
└── _resolve_all
    └── _resolve_title
        ├── _create_unmatched_movie
        └── _find_or_create_matched_movie
            └── _create_matched_movie
```

`execute` reads as named steps, and each method sits right below its caller:

```python
async def execute(self, input_data: InputData) -> OutputData:
    """Find or create one movie for each title a cinema shows.

    Args:
        input_data: The cinema and the titles it shows.

    Returns:
        The ID of the movie behind each title.

    Raises:
        CinemaNotFoundError: If the cinema does not exist.
    """
    await self._require_cinema(input_data.cinema_id)
    movies = await self._resolve_all(input_data.titles)
    logger.info("Added %d movies for %s", len(movies), input_data.cinema_id)
    return self.OutputData(movie_ids=tuple(movie.id.value for movie in movies))

async def _require_cinema(self, cinema_id: str) -> None:
    ...

async def _resolve_all(self, titles: tuple[str, ...]) -> list[Movie]:
    return [await self._resolve_title(title) for title in titles]

async def _resolve_title(self, title: str) -> Movie:
    ...
```
