# Marquise Development Guide

**Version**: 2.0  
**Audience**: All developers and AI coding assistants  
**Purpose**: Rules and standards that are actually enforced on this codebase

**Quick index**:
- What the system is → [ARCHITECTURE.md](ARCHITECTURE.md)
- Setup and commands → [CONTRIBUTING.md](CONTRIBUTING.md)
- Enforced rules → this document

---

## 1. Project Overview

**Marquise** is a Montreal cinema showtimes aggregator. It fetches screening data from Cineplex, CinemaCinema, Cinema Public, Cinéma Moderne, Cinémathèque québécoise, and Théâtre Outremont; normalises it; and stores it in a Supabase (PostgreSQL) database. The interface includes a Typer CLI, a read-only FastAPI REST API, and a public bootstrap API (`MarquiseFactory`) for apps in `apps/`.

Known technical debt and TODO items: [`docs/todo.md`](docs/todo.md).

---

## 2. Technology Stack

- **Language**: Python 3.13 (strict requirement)
- **Package manager**: `uv` — all commands use `uv run`, all deps via `uv add`
- **Database**: Supabase (PostgreSQL via `asyncpg`) — abstracted behind repository interfaces
- **CLI**: Typer + Rich
- **REST API**: FastAPI (read-only public endpoints + admin endpoints)
- **Testing**: pytest + pytest-asyncio
- **Code quality**: Ruff (formatting + linting) — mandatory before every commit
- **Coverage gate**: 70% CI minimum; target 80%+ overall, 100% for `domain/` and `application/`

**No exceptions**: Never use `pip` directly. All dependencies go through `uv`.

---

## 3. Clean Architecture — The Foundation

Marquise uses **Clean Architecture**. **Dependencies point inward only.** Outer layers depend on inner layers; inner layers never depend on outer layers.

```
┌──────────────────────────────────────┐
│  infrastructure/  (CLI, DB, sources) │
├──────────────────────────────────────┤
│  interface_adapters/  (repos, adapters) │
├──────────────────────────────────────┤
│  application/  (use cases, repo ABCs)│
├──────────────────────────────────────┤
│  domain/  (entities, value objects)  │
└──────────────────────────────────────┘
```

### 3.1 Layer Rules

**Domain** (innermost):
- Zero dependencies — standard library only
- Entities: `@dataclass(kw_only=True, slots=True)`, validate in `__post_init__`
- Value objects: `@dataclass(frozen=True, slots=True)`

**Application**:
- Imports from `domain` only — never from `interface_adapters` or `infrastructure`
- Each use case has inner `InputData` and `OutputData` as `@dataclass(frozen=True, slots=True)`
- Both `InputData` and `OutputData` **must** validate in `__post_init__`
- `execute(input: InputData) -> OutputData` is the only public method
- Repository interfaces are ABCs defined here — no concrete implementations

**Interface adapters**:
- Imports from `application` and `domain` — never from `infrastructure`
- Repository implementations: entity mapping only — no SQL here
- Gateway protocols: `typing.Protocol` types, stdlib + domain/application imports only

**Infrastructure**:
- The only layer allowed to import `asyncpg`, Supabase SDK, Typer, or external libraries
- Gateways execute SQL and return plain dicts — they never import domain entities
- CLI commands wire use cases to the terminal — business logic belongs in use cases

### 3.2 Boundary Rules

1. No circular imports
2. Domain never knows about databases, HTTP, or external systems
3. Application never knows about databases or HTTP
4. Interface adapters and infrastructure implement interfaces defined in application
5. Use cases catch domain exceptions and re-raise them as `ApplicationError` subclasses — domain exceptions must not escape the application layer

### 3.3 Public Surface & Import Boundary

Apps in `apps/` depend only on a defined public surface of `marquise-core` — never on internal modules.

**What is public** (defined in `marquise/__init__.py`, enforced via `__all__`):
- `MarquiseFactory` — dependency container with lazy-loaded controllers
- `create_factory()` — async factory function that returns a configured `MarquiseFactory`
- `create_factory_session()` — async context manager for request-scoped sessions
- `CinemaController`, `SourceController`, `AuthController` — thin wiring layer

**What is NOT public**: Domain entities, value objects, use cases, repositories, protocols, infrastructure.

**Import rules for `apps/`**:
- May import only from `marquise` (top-level) and `marquise.bootstrap`
- Must **never** import from `marquise.{domain,application,interface_adapters,infrastructure}`

**Enforcement**:
- AST-based scanner in `tests/unit_tests/test_import_boundary.py`
- `import-linter` contract in root `pyproject.toml`
- Snapshot test in `tests/unit_tests/test_public_api.py` prevents accidental `__all__` additions

---

## 4. Code Quality Standards

### 4.1 Type Hints — Mandatory Everywhere

Every function, method, and class attribute must have complete type hints. Use `str | None` (Python 3.10+ union syntax) — not `Optional[str]`.

```python
# Correct
async def find_by_name(self, name: str) -> Cinema | None: ...

# Forbidden — missing hints, old Optional syntax
def find(self, name):
    ...
```

### 4.2 Ruff — Run Before Every Commit

```bash
uv run ruff format .
uv run ruff check --fix .
```

Never manually style code — let Ruff handle it. Never commit code that fails either command.

### 4.3 Docstrings — Google Style

Every public module, class, method, and function must have a Google-style docstring.

```python
def fetch_cinemas(city: str, limit: int = 10) -> list[Cinema]:
    """Retrieve cinemas in a given city.

    Args:
        city: The city to filter by (case-insensitive).
        limit: Maximum number of results to return.

    Returns:
        A list of Cinema entities matching the filter.

    Raises:
        ValueError: If city is empty.
    """
```

Test functions must have docstrings describing the scenario under test.

### 4.4 Package Conventions

`__init__.py` files re-export symbols from submodules — they must not define classes or functions directly. Each logical group lives in its own file (`cinema.py`, `movie.py`, etc.).

### 4.5 Infrastructure Technology Isolation

Each external technology lives in its own subdirectory under `infrastructure/` and communicates with `interface_adapters/` through a `typing.Protocol` defined in `interface_adapters/repositories/protocols/`.

Rules:
- `interface_adapters/` never imports `asyncpg`, SQL strings, or any infrastructure module
- `infrastructure/<tech>/gateways/` fully owns SQL/API logic and returns plain dicts — no domain entity imports
- Protocol definitions use only stdlib and domain/application types

### 4.6 No Module-Level Mutable State

Never assign mutable objects at module level (global caches, lazy singletons). Each CLI invocation runs in its own process — there is no cross-call sharing.

Exception: `rich.Console()` is a stateless display-config object and is idiomatic at module level.

```python
# Forbidden
_container: Container | None = None

# Correct — fresh instance per command
@cinema_app.command()
def list_cinemas(...) -> None:
    controller = Container().cinema_controller
    ...
```

---

## 5. Testing

### 5.1 Organisation

Tests live under `packages/marquise-core/tests/`, not root-level `tests/` (see [§9.1 Workspace layout](#91-workspace-layout)):

```
packages/marquise-core/tests/
├── conftest.py          # shared fixtures
├── unit_tests/
│   ├── domain/          # entities, value objects
│   ├── application/     # use cases (repos mocked)
│   └── interface_adapters/  # adapter mapping (gateway mocked)
└── integration_tests/
    └── infrastructure/  # gateways with real DB
```

No `integration_tests/interface_adapters/` — that directory must not exist. Interface adapter tests are unit tests that mock the gateway protocol.

### 5.2 Test-by-Layer Rules

| Layer | Test type | What to mock |
|---|---|---|
| `domain/` | Unit | Nothing — pure Python |
| `application/` | Unit | Repository interfaces via `create_autospec` |
| `interface_adapters/` | Unit | Gateway protocols via `create_autospec` |
| `infrastructure/<tech>/gateways/` | Integration | Real database only |

### 5.3 Mocking

Use `unittest.mock.create_autospec` with the ABC or Protocol to enforce correct signatures:

```python
from unittest.mock import create_autospec

mock_repo = create_autospec(CinemaRepository, instance=True)
mock_repo.save.return_value = Cinema(...)

use_case = CreateCinemaUseCase(cinema_repository=mock_repo)
await use_case.execute(request)

mock_repo.save.assert_awaited_once()
```

Use `assert_awaited_once()` / `assert_awaited_once_with()` for async methods, `assert_not_awaited()` for verifying no call.

### 5.4 Async Tests

All async tests use `@pytest.mark.asyncio`. Tests are function-style — never class-style.

```python
@pytest.mark.asyncio
async def test_use_case_returns_cinema() -> None:
    """Use case returns a Cinema entity when the repo save succeeds."""
    ...
```

### 5.5 Coverage

```bash
# Check coverage
uv run pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-report=term-missing -q

# CI gate
uv run pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-fail-under=70
```

Target: 100% for `domain/` and `application/`. CI fails below 70%. Do not open a PR that drops coverage.

---

## 6. Pitfalls to Avoid

### Architecture violations

- Importing infrastructure classes in domain or application
- Using `asyncpg` or Supabase SDK outside `infrastructure/`
- Putting business logic in CLI commands, controllers, or repository implementations
- Creating circular dependencies between layers
- Using `Any` without a comment explaining why
- Importing internal modules from `apps/` (must only use `marquise` public surface)

### Quality gate violations

- Committing unformatted code (`ruff format --check` must pass)
- Committing lint errors (`ruff check` must pass)
- Committing failing tests
- Committing code that drops coverage below 70%

### Design violations

- Module-level mutable state (see §4.6)
- Domain exceptions escaping the application layer (see §3.1)
- Returning `dict` from repositories — return domain entities or value objects
- Putting query logic in use cases — keep it in repository implementations
- Mixing ORM/driver-specific types in domain — convert immediately in the gateway

---

## 7. Commands Reference

```bash
# ── All-in-one shortcuts (Makefile) ──────────────────────────────────
make test       # run all 3 test suites
make test-core  # core unit tests only
make test-api   # API tests only
make test-cli   # CLI tests only
make api        # launch API with hot reload
make cli        # launch CLI
make lint       # ruff check
make format     # ruff format
make ty         # type check marquise-core

# ── Manual equivalents ────────────────────────────────────────────────
# Unit tests (no DB required)
uv run --package marquise-core pytest packages/marquise-core/tests/unit_tests/ -q

# Unit tests with coverage
uv run --package marquise-core pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-report=term-missing -q

# API tests
uv run --package marquise-api pytest apps/marquise-api/tests -q

# CLI tests
uv run --package marquise-cli pytest apps/marquise-cli/tests -q

# Lint (workspace-wide, shared root config)
uv run ruff check .

# Type check (non-blocking in CI for now — see #34)
uv run ty check packages/marquise-core/src

# Format
uv run ruff format .

# Check formatting (CI mode)
uv run ruff format --check .

# CLI
uv run --package marquise-cli marquise-cli --help
uv run --package marquise-cli marquise-cli cinema --help
uv run --package marquise-cli marquise-cli source --help

# Add a runtime dependency to marquise-core
uv add --package marquise-core <package>

# Add a dev dependency (shared, root-level group)
uv add --dev <package>

# Sync after pyproject.toml changes (always from repo root — see §9.1)
uv sync
```

---

## 8. Process Guidelines

### Branch naming

- `feature/short-description`
- `fix/issue-description`
- `refactor/scope-description`
- `docs/scope-description`

### Commit messages

Format: `type(scope): concise description`  
Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### Pull request process

1. Rebase on main: `git pull origin main --rebase`
2. Run quality gates: `ruff format --check`, `ruff check`, `uv run --package marquise-core pytest packages/marquise-core/tests/unit_tests/`
3. Ensure coverage did not drop below 70%
4. Add `CHANGELOG.md` entry under the current date (or create a new date heading), noting which package(s) were affected. Bump version only in the affected package's `pyproject.toml` (`packages/marquise-core/pyproject.toml`, `apps/marquise-api/pyproject.toml`, or `apps/marquise-cli/pyproject.toml`). The root `pyproject.toml` is virtual and has no version of its own.
5. Reference the issue: `Closes #N`
6. Self-review the diff before requesting review

### Work incrementally

One focused task per commit. If a change touches >5 files or >2 layers, split it.

### Releasing

1. **Bump version** in the affected package's `pyproject.toml`.
2. **Add CHANGELOG entry** under the current date (or create a new date heading).
3. **Commit**: `chore(<pkg>): bump to vX.Y.Z`
4. **Tag**: `git tag marquise-core-vX.Y.Z` (or `marquise-api`, `marquise-cli`)
5. **Push**: `git push origin main --tags`
6. **CI** builds, publishes to PyPI, and creates a GitHub Release.

---

## 9. Frequently Confused Points

### 9.1 Workspace layout

Marquise is a `uv` workspace (`[tool.uv.workspace] members = ["packages/*", "apps/*"]`), mirroring the `packages/*` + `apps/*` convention already used by the `web/` pnpm monorepo. Root `pyproject.toml` is **virtual** — no `[project]`/`[build-system]` table, not a distributable package. It holds workspace config, the shared `dev` dependency group, and shared `ruff`/`ty` config only. `packages/marquise-core` is the sole member today; it owns its own `pyproject.toml`, runtime dependencies, the `marquise` console script, and `pytest`/coverage config.

When running pytest, target `packages/marquise-core/tests`, not a root-level `tests/` (it no longer exists). When running `ruff`/`ty`, invoke from repo root — those tools are shared/workspace-wide.

**One lockfile rule**: only run `uv sync` / `uv lock` from the repo root, never from inside `packages/marquise-core/` or any other member directory.

**InputData vs OutputData validation**: `InputData` validates because it represents external input. `OutputData` validates fields that are computed or transformed — skip re-validating values copied directly from already-validated entities.

**Controller vs use case**: Controllers (in `infrastructure/controllers/`) are thin wiring — `InputData` construction and delegation only. Business decisions go in use cases.

**Gateway vs repository**: Gateways (`infrastructure/<tech>/gateways/`) execute SQL and return plain dicts. Repositories (`interface_adapters/repositories/supabase/`) convert those dicts to domain entities.

---

*Last updated: 2026-06-26 — reflects Python 3.13, Supabase/asyncpg, Typer CLI, FastAPI REST API, and bootstrap API with import boundary enforcement.*
