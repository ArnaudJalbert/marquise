# Use case input and output

Read when writing `InputData` or `OutputData`.

- Each use case declares its own `InputData` and `OutputData` as immutable inner classes. They never live outside the use case. **Enforced:** `packages/marquise-core/tests/unit_tests/application/test_use_case_architecture.py` (its allowlist only shrinks).
- A use case never reuses another use case's input or output, so each one can change on its own. **Enforced:** `packages/marquise-core/tests/unit_tests/application/test_use_case_architecture.py`.
- `InputData` is the gateway into application logic, so it checks the types of its fields in `__post_init__`. This is the only place types are checked. The rest of the application trusts it.
- `OutputData` has no type checks.
- `InputData`, and any input class nested in it, only brings data into the use case through `execute`. Private methods don't receive it and inner classes don't hold it, so the outside contract can change without touching the logic.
- When the logic needs its own data structure, create a separate immutable inner class. Prefer them over complicated dicts or big tuples.

```python
class AddCinemaMoviesCommand:
    @dataclass(frozen=True, slots=True)
    class InputData:
        cinema_id: str
        titles: tuple[str, ...]

        def __post_init__(self) -> None:
            if not isinstance(self.cinema_id, str):
                raise TypeError("cinema_id must be a string")
            if not isinstance(self.titles, tuple):
                raise TypeError("titles must be a tuple")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movie_ids: tuple[str, ...]
```

An inner class names each value, so callers don't have to remember what a position or key means:

```python
@dataclass(frozen=True, slots=True)
class MatchedTitle:
    title: str
    tmdb_id: str

# Avoid: nothing says what each position means.
async def _create_matched_movie(self, matched: tuple[str, str]) -> Movie:
    ...

# Avoid: the keys are invisible to the reader and type checker.
async def _create_matched_movie(self, matched: dict[str, str]) -> Movie:
    ...

# Prefer: every value has a name and a type.
async def _create_matched_movie(self, matched: MatchedTitle) -> Movie:
    ...
```

`execute` is where input ends. Everything below it works with plain values or the use case's own classes:

```python
# Avoid: input leaks into the logic, tying it to the outside contract.
@dataclass(frozen=True, slots=True)
class MatchedTitle:
    source: MovieInput
    tmdb_id: str

async def _resolve_all(self, input_data: InputData) -> list[Movie]:
    ...

# Prefer: execute passes values on, and the logic has its own class.
@dataclass(frozen=True, slots=True)
class MatchedTitle:
    title: str
    tmdb_id: str

async def execute(self, input_data: InputData) -> OutputData:
    movies = await self._resolve_all(input_data.titles)
    ...
```
