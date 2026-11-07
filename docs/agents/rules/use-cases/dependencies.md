# Use case dependencies

Read when adding or changing what a use case receives or imports.

## Injection

- Every constructor dependency is required: no `| None`, no default value, and no branch on whether a collaborator is present. A use case has one execution path, so production and tests run the same code and wiring can't silently drop a step.
- A use case never resolves its dependencies: it doesn't construct them, look them up or fall back to one. The composition root (`infrastructure/di/`) builds them and passes them in.
- Only a coordinating use case may receive other use cases as injected dependencies, the same way as a repository. See [structure](structure.md#responsibility).
- A use case never imports another use case directly, and never imports a function from a use case to use as logic.
- An injected use case is imported under `TYPE_CHECKING` for its type hint only. The caller builds its input with `self._dependency.InputData(...)`, so nothing is imported at runtime and `InputData` stays an inner class.

```python
# Prohibited: an optional dependency, and one the use case builds itself.
def __init__(self, movie_repository: MovieRepository | None = None) -> None:
    self._movie_repository = movie_repository or SupabaseMovieRepository()

# Mandatory: everything is required and injected.
def __init__(
    self,
    movie_repository: MovieRepository,
    title_matcher: TitleMatcher,
) -> None:
    self._movie_repository = movie_repository
    self._title_matcher = title_matcher
```

A coordinating use case imports the others for their type hints only, and builds their input from the injected object:

```python
if TYPE_CHECKING:
    from marquise.application.queries.fetch_titles import FetchTitlesQuery

request = self._fetch_titles.InputData(cinema_id=input_data.cinema_id)
fetched = await self._fetch_titles.execute(request)
```

## Self-containment

- Write a new use case self-contained on the first pass. The only shared code it uses is its injected dependencies.
- Don't import code from other use cases or create general helpers on the first pass. Analyze what can be shared afterwards.
- The standard library, domain entities and value objects, application exceptions and the interfaces of injected dependencies are always fine to use. The restriction is on shared helper functions.

```python
# Prohibited on the first pass: logic imported from another use case.
from marquise.application.use_cases.match_title import normalize_title

# Mandatory on the first pass: a private method, even if it duplicates code.
def _normalized_title(self, title: str) -> str:
    return " ".join(title.split())
```
