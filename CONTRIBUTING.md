# Contributing to Marquise

## Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Setup

```bash
git clone https://github.com/arnaudjalbert/marquise.git
cd marquise
uv sync
cp .env.example .env   # fill in SUPABASE_URL, SUPABASE_KEY, DATABASE_URL
```

## Workspace layout

Marquise is a `uv` workspace (`[tool.uv.workspace] members = ["packages/*", "apps/*"]`). The root `pyproject.toml` is **virtual** — it has no `[project]`/`[build-system]` table and is not itself a distributable package. It holds only workspace config, the shared `dev` dependency group, and shared `ruff`/`ty` config (lint/type-check run repo-wide from root for one consistent pass). `packages/marquise-core` is the sole workspace member today; it owns its own `pyproject.toml`, runtime dependencies, `[project.scripts]` entry point, and `pytest`/coverage config, since test scope is inherently per-package. Future packages/apps each follow the same pattern: own `pyproject.toml` + own `tests/`, sharing the root's `ruff`/`ty` config and `dev` group.

**One lockfile rule**: only ever run `uv sync` / `uv lock` from the repo root, never from inside `packages/marquise-core/` or any other member directory. This keeps `uv.lock` single-sourced for the whole workspace.

### Bootstrap API

Apps in `apps/` access `marquise-core` through a public bootstrap API defined in `packages/marquise-core/src/marquise/bootstrap.py`. This is the **only** way external code should use the core package.

```python
from marquise import create_factory, create_factory_session

# Create a factory (one per application lifetime)
factory = await create_factory()

# Use controllers
cinemas = await factory.cinema.find_all()

# Or use a request-scoped session
async with create_factory_session() as session:
    await session.cinema.find_by_id(cinema_id)
```

**Import boundary**: Apps may **only** import from `marquise` (top-level) — never from `marquise.domain`, `marquise.application`, `marquise.interface_adapters`, or `marquise.infrastructure`. This is enforced by:
- AST-based scanner: `tests/unit_tests/test_import_boundary.py`
- `import-linter` contract in root `pyproject.toml`
- Snapshot test: `tests/unit_tests/test_public_api.py`

## Day-to-day commands

```bash
# Run unit tests (no DB required)
uv run pytest packages/marquise-core/tests/unit_tests/ -q

# Run all tests including integration (requires Supabase credentials)
uv run pytest packages/marquise-core/tests/ -q

# Run unit tests with coverage
uv run pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-report=term-missing -q

# Lint (workspace-wide, shared root config)
uv run ruff check .

# Auto-fix lint
uv run ruff check --fix .

# Type check (non-blocking in CI for now)
uv run ty check packages/marquise-core/src

# Format
uv run ruff format .

# Check formatting without modifying (what CI runs)
uv run ruff format --check .

# Explore the CLI
uv run --package marquise-cli marquise-cli --help

# Launch the API (hot reload)
uv run --package marquise-api uvicorn marquise_api.app:create_app --factory --reload --host 0.0.0.0 --port 8000
```

## CI pipeline

Every push and PR to `main` runs the `quality` job:

1. `ruff format --check` — fails on unformatted code
2. `ruff check` — fails on lint errors
3. `ty check packages/marquise-core/src` — type check; **non-blocking** for now (reports diagnostics without failing the build while the backlog is triaged, see #34)
4. `pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-fail-under=70` — fails below 70% coverage
5. Import boundary check — verifies `apps/` cannot import internal modules (via `import-linter` contract)

The `integration` job (manual trigger only) runs `packages/marquise-core/tests/integration_tests/` using secrets `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL`.

**Current coverage**: ~72% overall; 100% on domain and most of application.  
**CI gate**: 70% minimum. **Target**: 80%+ overall, 100% for `domain/` and `application/`.

## Branch naming

- `feature/short-description`
- `fix/issue-description`
- `refactor/scope-description`
- `docs/scope-description`

## Commit messages

Format: `type(scope): concise description`  
Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Examples:
```
feat(domain): add Movie.enrich() returning new instance
fix(use-case): rename updated_count docstring to say 'updated' not 'skipped'
docs(arch): add ARCHITECTURE.md
```

## PR checklist

- [ ] `ruff format --check` passes
- [ ] `ruff check` passes
- [ ] Unit tests pass (`pytest packages/marquise-core/tests/unit_tests/`)
- [ ] Coverage did not drop below 70%
- [ ] Import boundary not violated (`import-linter` passes)
- [ ] `CHANGELOG.md` entry added under the current date heading, noting which package(s) were affected
- [ ] Version bumped only in the affected package's `pyproject.toml` (semver: major/minor/patch)
- [ ] Issue linked in PR body (`Closes #N`)

## Reporting issues

- **Bugs**: include steps to reproduce, expected vs actual behaviour, Python version
- **Feature requests**: describe the problem and proposed solution
- **Security issues**: open a private vulnerability report on GitHub (do not open public issues)

## Architecture overview

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full layer diagram and key patterns.  
See [AGENTS.md](AGENTS.md) for development rules and coding standards.
