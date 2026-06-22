# Technical Debt & TODO

## Domain: Screening Entity References Full Objects

`Screening` currently holds full `Movie` and `Cinema` entity objects (not just their
IDs). Fields were renamed from `movie_id`/`cinema_id` to `movie`/`cinema` to be
honest about this. The coupling remains.

### Why it matters

- Loading full entities forces all callers to fetch related data even when they
  only need the ID (e.g., listing just screening IDs for a calendar view).
- Schema migrations or API changes to `Movie` / `Cinema` could force changes to
  `Screening` tests and logic.
- It blurs the boundary between domain entities and application-layer DTOs.

### Desired fix

3. Move any cross-entity logic (e.g., "is this movie playing at this cinema")
   into the application layer (use cases).
4. Update all tests accordingly.
5. Update `Screening.__str__()` to not rely on full entity reference.

## Type Hint Inconsistency: `str | None` vs `Optional[str]`

9 occurrences of `str | None` across the codebase while the convention uses
`Optional[str]` from `typing`.

### Files to fix

- `domain/entities/source_definition.py:22`
- `application/repositories/cinema_repository.py:70`
- `interface_adapters/repositories/protocols/cinema.py:116`
- `interface_adapters/repositories/supabase/cinema_repository.py:104`
- `infrastructure/controllers/cinema_controller.py:75`
- `infrastructure/controllers/source_controller.py:48`
- `infrastructure/cli/cinema_commands.py:201`
- `infrastructure/supabase/gateways/cinema.py:192`
- `infrastructure/sources/cinemacinema/gateways/source.py:70`

## Infrastructure: Repeated `import asyncio` Inside CLI Closures

11 occurrences across `cinema_commands.py` and `source_commands.py` where
`import asyncio` is placed inside async `_run()` closures. Should be a top-level
import.

## Infrastructure: Dead Function `_select_cinema_public`

`_select_cinema_public` in `source_commands.py:499-515` is defined but never
called. Only `_select_cinema_admin` is used. Remove or implement the missing
call site.

## Infrastructure: `GatewayError` Lives in Wrong Module

`GatewayError` is defined in `protocols/cinema.py` but used by all gateway
protocols (source_definition, cinema_source_assignment). Should be in
`protocols/base.py`.

## Infrastructure: `__inserted` Flag is a Leaky Abstraction

`ScreeningGateway.save()` returns a plain `dict` but includes an undocumented
`__inserted` boolean key. The protocol's docstring now documents this, but a
cleaner fix would make it part of the type signature (e.g., returning a
`NamedTuple`).

## Domain: `Movie.is_recent` Uses Naive `datetime.now()`

`Movie.is_recent` (movie.py:59-61) uses naive `datetime.now()` while
`Screening.is_upcoming` uses timezone-aware `datetime.now(timezone.utc)`.
Inconsistent. Should standardize to timezone-aware.

## Tests: Empty Root `conftest.py`

`tests/conftest.py` contains only a docstring. Should contain shared fixtures
(e.g., `sample_cinema`, `sample_movie`) per AGENTS.md Section 9.4. Many test
files currently define their own local fixtures that could be shared.

## Cleanup: Stale `__pycache__` Files

Multiple stale `.pyc` files exist for deleted source files:

- `domain/value_objects/__pycache__/parameter_definition.cpython-313.pyc`
- `domain/value_objects/__pycache__/source_parameters.cpython-313.pyc`
- `tests/__pycache__/test_showtime_source.cpython-313-pytest-9.0.3.pyc`
- `tests/__pycache__/test_source_parameters.cpython-313-pytest-9.0.3.pyc`
- `tests/__pycache__/test_parameter_definition.cpython-313-pytest-9.0.3.pyc`

Run `find . -name '*.pyc' -delete && find . -name '__pycache__' -type d -empty -delete`.

---

## Docstrings: NumPy Style in Gateways

`SupabaseMovieGateway` and `SupabaseScreeningGateway` use NumPy-style
docstrings (`Parameters` / `Returns` sections) while AGENTS.md mandates
Google-style (`Args:` / `Returns:`).

### Files to fix

- `infrastructure/supabase/gateways/movie.py`
- `infrastructure/supabase/gateways/screening.py`

## Dead Code: `_parse_datetime` `str` Branch Unreachable

`_parse_datetime` in `screening_repository.py:28-42` accepts `datetime | str`
and has a `str` fallback, but asyncpg always returns `datetime` for TIMESTAMP
columns. The `str` branch is dead code.

### Desired fix

1. Change the parameter type to `datetime` only.
2. Remove the `fromisoformat` / `strptime` fallback logic.
3. Remove the `MovieId` and `Showtime` import if all their callers were removed
   (check after dead code removal).

## Missing Validation: `ShowtimeRow` Has No `__post_init__`

`ShowtimeRow` (in `source_registry_query.py`) has no `__post_init__` validation
per AGENTS.md Section 4.2 ("Both InputData and OutputData MUST validate data in
`__post_init__`"). Allows empty strings for `movie_title` and `showtime`.

### Desired fix

Add `__post_init__` that rejects empty `movie_title` and `showtime`.

## Security: SSL Verification Disabled in Scrapers

Both `cinemapublic/gateways/source.py` and `cinemacinema/gateways/source.py`
use `ssl._create_unverified_context()` to fetch data. This disables certificate
verification.

### Desired fix

- Add a config option to enable verification in production.
- Document why it's disabled (likely self-signed or expired certs on the
  scraped sites).