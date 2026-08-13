# Technical Debt & TODO

Read before refactoring related areas.

---

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
(e.g., `sample_cinema`, `sample_movie`). Many test files currently define their
own local fixtures that could be shared.

## Cleanup: Stale `__pycache__` Files

Multiple stale `.pyc` files exist for deleted source files. Run:

```bash
find . -name '*.pyc' -delete && find . -name '__pycache__' -type d -empty -delete
```

## Docstrings: NumPy Style in Gateways

`SupabaseMovieGateway` and `SupabaseScreeningGateway` use NumPy-style
docstrings while [python.md](python.md) mandates Google-style.

### Files to fix

- `infrastructure/supabase/gateways/movie.py`
- `infrastructure/supabase/gateways/screening.py`

## Dead Code: `_parse_datetime` `str` Branch Unreachable

`_parse_datetime` in `screening_repository.py:28-42` accepts `datetime | str`
but asyncpg always returns `datetime` for TIMESTAMP columns.

## Missing Validation: `ShowtimeRow` Has No `__post_init__`

`ShowtimeRow` has no validation — allows empty strings for `movie_title` and
`showtime`.

## Security: SSL Verification Disabled in Scrapers

`cinemapublic/gateways/source.py` and `cinemacinema/gateways/source.py` use
`ssl._create_unverified_context()`. Add a config option for production; document
why it is disabled.
