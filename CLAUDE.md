# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Unit tests (no DB required)
uv run pytest packages/marquise-core/tests/unit_tests/ -q

# Single test file or test
uv run pytest packages/marquise-core/tests/unit_tests/domain/test_cinema.py -q
uv run pytest packages/marquise-core/tests/unit_tests/ -k "test_name" -q

# Unit tests with coverage
uv run pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-report=term-missing -q

# Integration tests (requires real Supabase credentials)
uv run pytest packages/marquise-core/tests/ -q

# Lint (workspace-wide, shared root config)
uv run ruff check .

# Auto-fix lint
uv run ruff check --fix .

# Format
uv run ruff format .

# Check formatting (CI mode)
uv run ruff format --check .

# Type check (non-blocking in CI — see issue #34)
uv run ty check packages/marquise-core/src

# CLI
uv run marquise --help

# Add dependency
uv add --package marquise-core <package>   # runtime
uv add --dev <package>                     # dev only, shared root group
```

Never use `pip` directly. All dependencies go through `uv`.

## Workspace layout

Marquise is a `uv` workspace (`[tool.uv.workspace] members = ["packages/*", "apps/*"]`), mirroring the `packages/*` + `apps/*` convention used by the `web/` pnpm monorepo. Root `pyproject.toml` is virtual — no `[project]`/`[build-system]` table, not a distributable package; it holds only workspace config, the shared `dev` dependency group, and shared `ruff`/`ty` config. `packages/marquise-core` is the sole member today, owning its own `pyproject.toml`, runtime dependencies, the `marquise` console script, and `pytest`/coverage config. Only run `uv sync`/`uv lock` from the repo root — never from inside a package directory — so `uv.lock` stays single-sourced for the whole workspace.

## Architecture

Marquise is a Montreal cinema showtimes aggregator. It follows **Clean Architecture** with strict inward-only dependencies across four layers:

```
infrastructure/        ← CLI (Typer), DI container, scrapers, raw SQL gateways
interface_adapters/    ← Repository implementations, source adapters, gateway protocols
application/           ← Use cases, repository ABCs, exceptions
domain/                ← Entities (Cinema, Movie, Screening), value objects
```

### Layer dependency rules

- **Domain**: zero external dependencies — stdlib only. Entities are `@dataclass(kw_only=True, slots=True)`. Value objects are `@dataclass(frozen=True, slots=True)`. Validation in `__post_init__`.
- **Application**: imports `domain` only. Use cases have `InputData`/`OutputData` as `@dataclass(frozen=True, slots=True)`, both validated in `__post_init__`. `execute(input: InputData) -> OutputData` is the only public method. Domain exceptions must be caught and re-raised as `ApplicationError` subclasses — they must not escape this layer.
- **Interface adapters**: imports `application` and `domain` — never `infrastructure`. Repository implementations do entity mapping only (no SQL). Gateway protocols are `typing.Protocol` types.
- **Infrastructure**: the only layer allowed to import `asyncpg`, Supabase SDK, Typer, or external libs. Gateways execute SQL and return plain dicts — they never import domain entities.

### Key patterns

**Gateway → Repository → Use case**:
- `infrastructure/supabase/gateways/` — raw SQL via asyncpg, returns plain `dict`
- `interface_adapters/repositories/protocols/` — `typing.Protocol` types that gateways implement
- `interface_adapters/repositories/supabase/` — convert gateway dicts to domain entities
- `application/repositories/` — abstract interfaces (ABCs) that repositories implement

**Source adapters** (`interface_adapters/repositories/source_adapters/`): translate raw `ShowtimeRow` dicts from scrapers (`infrastructure/sources/<source>/`) into use-case-ready format. `source_registry.py` maps source names to adapter classes at runtime.

**DI**: `infrastructure/di/` contains the container. Controllers (`infrastructure/controllers/`) are thin wiring — construct `InputData` and delegate to a use case. No business logic in controllers or CLI commands.

**No module-level mutable state**: each CLI invocation is a fresh process. Create new instances per command (see §4.6 in AGENTS.md for the pattern).

### Data flow

```
uv run marquise source import
  → CLI (infrastructure/cli/source_commands.py)
  → Controller (infrastructure/controllers/)
  → ImportScreeningsUseCase (application/use_cases/)
    → SourceAdapter.fetch_showtimes()    # HTTP
    → MovieRepository.find_by_title()   # Supabase
    → MovieRepository.save()
    → ScreeningRepository.save()        # upsert
  → Output via Rich
```

## Testing conventions

- All tests are function-style (never class-style), async tests use `@pytest.mark.asyncio`.
- Mock with `unittest.mock.create_autospec(SomeABC, instance=True)` — enforces correct signatures.
- Use `assert_awaited_once()` / `assert_not_awaited()` for async methods.
- `interface_adapters/` tests are unit tests that mock the gateway protocol — there is no `integration_tests/interface_adapters/` directory.
- Every test function needs a docstring describing the scenario.

Tests live under `packages/marquise-core/tests/`, not root-level `tests/`.

| Layer | Test location | Mock |
|---|---|---|
| `domain/` | `packages/marquise-core/tests/unit_tests/domain/` | Nothing |
| `application/` | `packages/marquise-core/tests/unit_tests/application/` | Repository ABCs |
| `interface_adapters/` | `packages/marquise-core/tests/unit_tests/interface_adapters/` | Gateway protocols |
| `infrastructure/gateways/` | `packages/marquise-core/tests/integration_tests/` | Real DB only |

## Code standards

- **Type hints**: mandatory everywhere. Use `str | None` (not `Optional[str]`).
- **Docstrings**: Google style on every public module, class, method, and function.
- **`__init__.py`**: re-exports only — no class or function definitions.
- Returning `dict` from repositories is forbidden — return domain entities or value objects.
- Using `Any` requires a comment explaining why.

## Environment variables

Required in `.env`:
- `DATABASE_URL` — PostgreSQL connection string
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_PUBLISHABLE_KEY` — Supabase anon key

Optional:
- `CINEPLEX_API_KEY` — `Ocp-Apim-Subscription-Key` header value
- `DATABASE_SCHEMA` — schema name (default: `marquise`)

## PR / commit conventions

Branch: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`  
Commit: `type(scope): concise description`

Before opening a PR: run `ruff format --check`, `ruff check`, `pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-fail-under=70`, add a `CHANGELOG.md` entry with a version heading (repo-level; the root `pyproject.toml` is virtual and has no version of its own), and bump `packages/marquise-core/pyproject.toml`'s `version` if that package's code changed.
