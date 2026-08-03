# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Core unit tests (no DB required)
uv run pytest packages/marquise-core/tests/unit_tests/ -q

# Single test file or test
uv run pytest packages/marquise-core/tests/unit_tests/domain/test_cinema.py -q
uv run pytest packages/marquise-core/tests/unit_tests/ -k "test_name" -q

# Core unit tests with coverage
uv run pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-report=term-missing -q

# App tests (no DB required — the DI factory is mocked).
# Run each suite in its own pytest invocation: each app has its own
# [tool.pytest.ini_options], and combining suites in one command breaks
# rootdir/pythonpath resolution.
uv run pytest apps/marquise-api/tests/ -q
uv run pytest apps/marquise-cli/tests/ -q

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

# Run the CLI / the API
uv run marquise --help
uv run marquise-api

# Add dependency (runtime deps go to the member that needs them)
uv add --package marquise-core <package>
uv add --package marquise-api <package>
uv add --package marquise-cli <package>
uv add --dev <package>                     # dev only, shared root group
```

Never use `pip` directly. All Python dependencies go through `uv`.

## Workspace layout

Marquise is a `uv` workspace (`[tool.uv.workspace] members = ["packages/*", "apps/*"]`) with three members:

- `packages/marquise-core` — the domain library (Clean Architecture, importable as `marquise`)
- `apps/marquise-api` — read-only FastAPI app (`marquise_api`, console script `marquise-api`)
- `apps/marquise-cli` — Typer administration CLI (`marquise_cli`, console script `marquise`)

Root `pyproject.toml` is virtual — no `[project]`/`[build-system]` table, not a distributable package; it holds only workspace config, the shared `dev` dependency group, shared `ruff`/`ty` config, and the import-linter contracts. Each member owns its own `pyproject.toml`, runtime dependencies, console scripts, and `pytest` config. Only run `uv sync`/`uv lock` from the repo root — never from inside a package directory — so `uv.lock` stays single-sourced for the whole workspace.

## Architecture

Marquise is a Montreal cinema showtimes aggregator. `marquise-core` follows **Clean Architecture** with strict inward-only dependencies across four layers:

```
infrastructure/        ← DI container, controllers, scrapers, raw SQL gateways, auth
interface_adapters/    ← Repository implementations, source adapters, gateway protocols
application/           ← Use cases, repository ABCs, exceptions
domain/                ← Entities (Cinema, Movie, Screening), value objects
```

The API and CLI apps are thin delivery mechanisms on top of core. They may import **only the public facade** — `from marquise import ...` (exceptions, use cases, controllers, `MarquiseFactory`/`create_factory`). Importing `marquise.domain`, `marquise.application`, `marquise.interface_adapters`, or `marquise.infrastructure` from an app is forbidden and enforced by the import-linter contract `apps-use-public-surface-only` in the root `pyproject.toml`. Anything an app needs must be re-exported from `marquise/__init__.py` (via `marquise.bootstrap`).

### Layer dependency rules (inside marquise-core)

- **Domain**: zero external dependencies — stdlib only. Entities are `@dataclass(kw_only=True, slots=True)`. Value objects are `@dataclass(frozen=True, slots=True)`. Validation in `__post_init__`.
- **Application**: imports `domain` only. Use cases have `InputData`/`OutputData` as `@dataclass(frozen=True, slots=True)`, both validated in `__post_init__`. `execute(input: InputData) -> OutputData` is the only public method. Domain exceptions must be caught and re-raised as `ApplicationError` subclasses — they must not escape this layer.
- **Interface adapters**: imports `application` and `domain` — never `infrastructure`. Repository implementations do entity mapping only (no SQL). Gateway protocols are `typing.Protocol` types.
- **Infrastructure**: the only core layer allowed to import `asyncpg`, the Supabase SDK, or other external libs. Gateways execute SQL and return plain dicts — they never import domain entities. (Typer/Rich/FastAPI live in the apps, not in core.)

### Key patterns

**Gateway → Repository → Use case**:
- `infrastructure/supabase/gateways/` — raw SQL via asyncpg, returns plain `dict`
- `interface_adapters/repositories/protocols/` — `typing.Protocol` types that gateways implement
- `interface_adapters/repositories/supabase/` — convert gateway dicts to domain entities
- `application/repositories/` — abstract interfaces (ABCs) that repositories implement

**Source adapters** (`interface_adapters/repositories/source_adapters/`): translate raw `ShowtimeRow` dicts from scrapers (`infrastructure/sources/<source>/`) into use-case-ready format. `source_registry.py` maps source names to adapter classes at runtime.

**DI**: `infrastructure/di/` contains the container. Controllers (`infrastructure/controllers/`) are thin wiring — construct `InputData` and delegate to a use case. Apps obtain fully-wired controllers through `MarquiseFactory` / `create_factory` (`marquise/bootstrap.py`), which also owns the DB pool lifecycle. No business logic in controllers, CLI commands, or API routers.

**No module-level mutable state**: each CLI invocation is a fresh process. Create new instances per command (see §4.6 in AGENTS.md for the pattern).

### Data flow

```
uv run marquise source import
  → CLI command (apps/marquise-cli/src/marquise_cli/source_commands.py)
  → MarquiseFactory → Controller (core infrastructure/controllers/)
  → ImportScreeningsUseCase (application/use_cases/)
    → SourceAdapter.fetch_showtimes()    # HTTP
    → MovieRepository.find_by_title()   # Supabase
    → MovieRepository.save()
    → ScreeningRepository.save()        # upsert
  → Output via Rich
```

The API follows the same shape: FastAPI router (`apps/marquise-api/src/marquise_api/routers/`) → controller from the factory → use case.

## Testing conventions

- All tests are function-style (never class-style), async tests use `@pytest.mark.asyncio`.
- Mock with `unittest.mock.create_autospec(SomeABC, instance=True)` — enforces correct signatures.
- Use `assert_awaited_once()` / `assert_not_awaited()` for async methods.
- `interface_adapters/` tests are unit tests that mock the gateway protocol — there is no `integration_tests/interface_adapters/` directory.
- Every test function needs a docstring describing the scenario.

Core tests live under `packages/marquise-core/tests/`; each app owns its tests under `apps/<app>/tests/`.

| Code | Test location | Mock |
|---|---|---|
| `domain/` | `packages/marquise-core/tests/unit_tests/domain/` | Nothing |
| `application/` | `packages/marquise-core/tests/unit_tests/application/` | Repository ABCs |
| `interface_adapters/` | `packages/marquise-core/tests/unit_tests/interface_adapters/` | Gateway protocols |
| `infrastructure/gateways/` | `packages/marquise-core/tests/integration_tests/` | Real DB only |
| `apps/marquise-api/` | `apps/marquise-api/tests/` | `MarquiseFactory` (no DB) |
| `apps/marquise-cli/` | `apps/marquise-cli/tests/` | `MarquiseFactory` (no DB) |

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

Before opening a PR:
- Run `uv run ruff format --check .` and `uv run ruff check .`
- Run `uv run pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-fail-under=70`
- If an app was touched, run its test suite (`uv run pytest apps/<app>/tests/ -q`)
- Add a `CHANGELOG.md` entry under the current date noting which package(s) were affected
- Bump version only in the affected package's `pyproject.toml` (`packages/marquise-core/`, `apps/marquise-api/`, or `apps/marquise-cli/`)
