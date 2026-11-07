# Use case input and output

Read when writing `InputData` or `OutputData`.

- Each use case declares its own `InputData` and `OutputData` as immutable inner classes. They never live outside the use case. **Enforced:** `packages/marquise-core/tests/unit_tests/application/test_use_case_architecture.py` (its allowlist only shrinks).
- A use case never reuses another use case's input or output, so each one can change on its own. **Enforced:** `packages/marquise-core/tests/unit_tests/application/test_use_case_architecture.py`.
- `InputData` is the gateway into application logic, so it checks the types of its fields in `__post_init__`. This is the only place types are checked. The rest of the application trusts it.
- `OutputData` has no type checks.
- `InputData`, and any input class nested in it, only brings data into the use case through `execute`. Private methods don't receive it and inner classes don't hold it, so the outside contract can change without touching the logic.
- Work with domain entities whenever they fit. Most of the time the logic can use the entity.
- When no entity fits, use the data classes that repositories and readers return, not the database structure behind them. This avoids redefining the same data.
- Only when neither fits, create a separate immutable inner class. Its only purpose is to replace a big tuple or a complicated dict, and both are prohibited.

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

# Prohibited: nothing says what each position means.
async def _create_matched_movie(self, matched: tuple[str, str]) -> Movie:
    ...

# Prohibited: the keys are invisible to the reader and type checker.
async def _create_matched_movie(self, matched: dict[str, str]) -> Movie:
    ...

# Mandatory: every value has a name and a type.
async def _create_matched_movie(self, matched: MatchedTitle) -> Movie:
    ...
```

`execute` is where input ends. Everything below it works with plain values or the use case's own classes:

```python
# Prohibited: input leaks into the logic, tying it to the outside contract.
@dataclass(frozen=True, slots=True)
class MatchedTitle:
    source: MovieInput
    tmdb_id: str

async def _match_titles(self, input_data: InputData) -> TitleMatches:
    ...

# Mandatory: execute passes values on, and the logic has its own class.
@dataclass(frozen=True, slots=True)
class MatchedTitle:
    title: str
    tmdb_id: str

async def execute(self, input_data: InputData) -> OutputData:
    matches = await self._match_titles(input_data.titles)
    ...
```
