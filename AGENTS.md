# Marquise Development Guide

**Version**: 2.0  
**Audience**: All developers, with emphasis on AI coding assistants  
**Quick index**: Architecture → [ARCHITECTURE.md](ARCHITECTURE.md) · Setup & commands → [CONTRIBUTING.md](CONTRIBUTING.md) · Rules → here

## 1. Project Overview

**Marquise** is an open-source platform for aggregating and exploring movie showtimes in Montreal. It gathers screening data from three sources (Cineplex, CinemaCinema, CinemaPublic), normalizes it, and exposes it through a Typer CLI. A read-only FastAPI REST API is planned but **not yet implemented**.

Known technical debt is tracked in [`docs/todo.md`](docs/todo.md). Check this file before starting new work to avoid duplicating effort.

## 2. Technology Stack

- **Language**: Python 3.13 (strict requirement)
- **Package Manager**: `uv` — all dependency management and command execution. Never use `pip` directly.
- **Database**: Supabase (PostgreSQL via `asyncpg`) — abstracted behind repository interfaces
- **CLI**: Typer + Rich
- **API**: FastAPI — planned, not yet implemented
- **Testing**: pytest + pytest-asyncio
- **Code Quality**: Ruff (formatting + linting); type hints mandatory everywhere

## 3. Clean Architecture — The Foundation

Marquise strictly follows Clean Architecture. **Dependencies point inward only** — outer layers can depend on inner layers, but inner layers never depend on outer layers.

```
┌────────────────────────────────────────────────────────┐
│  src/marquise/infrastructure/                          │
├────────────────────────────────────────────────────────┤
│  src/marquise/interface_adapters/                      │
├────────────────────────────────────────────────────────┤
│  src/marquise/application/                             │
├────────────────────────────────────────────────────────┤
│  src/marquise/domain/                                  │
└────────────────────────────────────────────────────────┘
```

### 3.1 Layer responsibilities

**Domain** (innermost):
- Entities (`Cinema`, `Movie`, `Screening`, …) — `@dataclass(kw_only=True, slots=True)`
- Value objects — immutable, defined by their attributes
- Zero external dependencies — stdlib only
- Validate data in `__post_init__`

**Application**:
- Use cases — each defines `InputData` and `OutputData` as inner frozen dataclasses with `__post_init__` validation
- Repository interfaces — ABCs in `application/repositories/`
- Application exceptions — `ApplicationError` subclasses; domain exceptions must not leak past this boundary
- No database or HTTP knowledge allowed

**Interface adapters**:
- Repository implementations in `repositories/supabase/` — map gateway dicts ↔ domain entities
- Gateway protocols in `repositories/protocols/` — `typing.Protocol` definitions; no SQL or infrastructure imports
- Source adapters in `repositories/source_adapters/` — bridge `Cinema` entities to source-specific fetch parameters

**Infrastructure**:
- CLI (Typer), DI container (`di/container.py`), Supabase gateways (SQL), config, external scraper sources
- The only layer with direct database or external API dependencies
- Wires everything together; imports from all inner layers

### 3.2 Boundary rules

1. **No circular imports** — if you see them, the architecture is broken
2. **Domain never imports** from application, interface_adapters, or infrastructure
3. **Application never imports** database clients, HTTP libraries, or infrastructure classes
4. **`interface_adapters/repositories/protocols/`** uses only stdlib and domain/application types — never `asyncpg` or SQL strings
5. **`infrastructure/supabase/gateways/`** owns all SQL and never imports from `domain/entities/` — returns plain dicts only

## 4. Development Environment

See [CONTRIBUTING.md](CONTRIBUTING.md) for full setup instructions and day-to-day commands.

Quick reference:
```bash
uv sync
uv run pytest tests/unit_tests/ -q
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## 5. Code Quality Standards

### 5.1 Type Hints — 100% Mandatory

Every function, method, and class must have complete type hints. Use `X | None` (not `Optional[X]`) on Python 3.13. Prefer specific types over `Any`; if `Any` is necessary, add a comment explaining why.

### 5.2 Ruff Formatting and Linting

```bash
uv run ruff format .
uv run ruff check --fix
```

Never manually style code — let ruff handle it. Never commit code that fails either command.

### 5.3 Docstrings (Google Style)

Every public module, class, method, and function must have a Google-style docstring. Test functions must describe the scenario they test.

```python
def fetch_cinemas(city: str, limit: int = 10) -> list[Cinema]:
    """Retrieve cinemas in a given city.

    Args:
        city: The city to filter by (case-insensitive).
        limit: Maximum number of results to return.

    Returns:
        A list of Cinema entities matching the filter.

    Raises:
        ValueError: If city is empty or whitespace-only.
    """
```

### 5.4 Package Conventions — `__init__.py` for Re-exports Only

`__init__.py` files must only re-export symbols from dedicated submodules. Never define classes or functions in them.

```python
# ✅ correct
from marquise.domain.exceptions.cinema import CinemaError
__all__ = ["CinemaError"]

# ❌ forbidden
class CinemaError(Exception): ...
```

### 5.5 Infrastructure Technology Isolation (Gateway Pattern)

Each external technology lives in its own subdirectory under `infrastructure/` and communicates with `interface_adapters` through a `typing.Protocol`.

Pattern:
1. **Define a Protocol** in `interface_adapters/repositories/protocols/` — no SQL, no infrastructure imports
2. **Implement the Protocol** in `infrastructure/<tech>/gateways/` — SQL and external API calls live here
3. **Adapt in interface_adapters** — the repository implementation takes the protocol as a dependency and handles entity mapping only

### 5.6 Testing by Layer

| Layer | Test type | Mocking |
|---|---|---|
| `domain/` | Unit | None needed |
| `application/` | Unit | Repos mocked via `create_autospec` |
| `interface_adapters/` | Unit only | Gateway mocked — no real DB |
| `infrastructure/<tech>/gateways/` | Integration | Real database |

Key rules:
- `interface_adapters/` tests must not require a database connection — mock the gateway protocol
- `tests/integration/` mirrors `src/marquise/infrastructure/` — only infrastructure classes get integration tests
- `tests/integration/interface_adapters/` must not exist

### 5.7 Test Coverage

**CI gate**: 80% minimum (`fail_under = 80` in `pyproject.toml`).  
**Target**: 100% for `domain/` and `application/` layers — do not add uncovered lines in these layers without a strong reason.  
**Infrastructure**: "good" coverage; 100% not strictly required, but critical paths must be covered by integration tests.

```bash
# Check coverage
uv run pytest tests/unit_tests/ --cov=marquise --cov-report=term-missing
```

## 6. Use Case Conventions

Every use case **must**:
- Define `InputData` and `OutputData` as inner `@dataclass(frozen=True, slots=True)` classes
- Validate both in `__post_init__` — `InputData` guards external boundaries; `OutputData` catches programming errors in output construction
- Accept `InputData` and return `OutputData` from `execute()`
- Raise `ApplicationError` subclasses only — never let domain exceptions escape past the use case

```python
class CreateCinemaUseCase:
    @dataclass(frozen=True, slots=True)
    class InputData:
        name: str
        address: str

        def __post_init__(self) -> None:
            if not self.name.strip():
                raise ValueError("name must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        cinema_id: str
        name: str

        def __post_init__(self) -> None:
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")

    async def execute(self, request: InputData) -> OutputData:
        ...
```

## 7. Testing Conventions

### Function-style tests — no classes

```python
# ✅ correct
async def test_cinema_creation() -> None: ...

# ❌ forbidden
class TestCinema:
    def test_creation(self) -> None: ...
```

### Mock repositories with `create_autospec`

```python
mock_repo = create_autospec(CinemaRepository, instance=True)
mock_repo.find_by_name_and_address.return_value = None
mock_repo.save.return_value = Cinema(...)
```

Use `assert_awaited_once()` / `assert_awaited_once_with()` for async methods, `assert_not_awaited()` to verify a method was never called.

## 8. Pitfalls to Avoid

### 8.1 Architecture violations

**Never**:
- Import infrastructure classes in domain or application
- Put business logic in CLI commands, routes, or repository implementations
- Create circular imports between layers
- Use `Any` type without a comment explaining why

If you catch yourself doing any of these, stop and refactor.

### 8.2 Mutable module-level state

Never use module-level mutable singletons (global caches, lazily-initialized globals). Each CLI command runs in its own process — module-level singletons offer no benefit and break testability. Use the `Container` DI class instead.

```python
# ❌ forbidden
_cinema_repo: CinemaRepository | None = None

# ✅ correct — fresh instance per call
@cinema_app.command()
def list_cinemas() -> None:
    controller = Container().cinema_controller
    ...
```

Exception: `Console()` from Rich is stateless and acceptable at module level.

### 8.3 Domain exceptions leaking past use cases

Use cases must catch domain exceptions and re-raise as `ApplicationError` subclasses. CLI commands and (when added) API routes must never import from `marquise.domain.exceptions`.

```python
# ❌ forbidden — domain exception escapes the use case
from marquise.domain.exceptions import CinemaNotFoundError
raise CinemaNotFoundError(...)

# ✅ correct
from marquise.application.exceptions import CinemaNotFoundError
raise CinemaNotFoundError(...)
```

### 8.4 Overly large changes

If a change touches >5 files or >2 layers, split it into smaller PRs. One commit = one focused change.

### 8.5 Skipping quality gates

Never commit code that:
- Fails `uv run ruff format --check .`
- Fails `uv run ruff check`
- Has failing tests
- Drops overall coverage below 80%

## 9. Commands Reference

```bash
# Format code
uv run ruff format .

# Lint (and auto-fix)
uv run ruff check --fix

# Unit tests
uv run pytest tests/unit_tests/ -q

# All tests (requires Supabase credentials)
uv run pytest tests/ -q

# Tests with coverage report
uv run pytest tests/unit_tests/ --cov=marquise --cov-report=term-missing

# Add a runtime dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Sync after pyproject.toml changes
uv sync

# Run CLI
uv run marquise --help
```

## 10. Process Guidelines

### Branch naming
- `feature/short-description`
- `fix/short-description`
- `docs/short-description`
- `refactor/short-description`

### Commit messages

Format: `type(scope): concise description`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Examples:
- `feat(domain): add Promotion entity with validation logic`
- `fix(import): correct updated_count docstring`
- `docs: rewrite AGENTS.md to match current architecture`
- `refactor(repo): remove __inserted dict key, introduce SaveResult`

### Pull request process

1. Rebase on main before opening: `git pull origin main --rebase`
2. Run all quality gates: ruff format, ruff check, pytest with coverage
3. Add a `CHANGELOG.md` entry and bump the version in `pyproject.toml`
4. Reference the relevant issue in the PR description
5. Self-review before requesting review

### Work incrementally

One focused task per commit. If your change spans more than two layers, split it into separate commits or PRs.

---

**Last Updated**: 2026-06-26  
**See also**: [ARCHITECTURE.md](ARCHITECTURE.md) — what the system is · [CONTRIBUTING.md](CONTRIBUTING.md) — how to work on it
