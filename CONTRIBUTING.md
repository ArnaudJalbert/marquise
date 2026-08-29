# Contributing to Marquise

This repository — setup, commands, paths, and CI. For the operating process see
[Atlas Documentation and Delivery Workflow](atlas/50-processes/Documentation%20and%20Delivery%20Workflow.md); for design principles see
[Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md). For enforced rules see [AGENTS.md](AGENTS.md).

---

## Prerequisites

**Python backend**

- Python 3.13
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

**Web frontend** (only if working in `web/`)

- [Node.js](https://nodejs.org/) ≥ 20
- [pnpm](https://pnpm.io/) 11.x via Corepack: `corepack enable pnpm`

## Setup

### Python

```bash
git clone https://github.com/ArnaudJalbert/marquise.git
cd marquise
uv sync
cp .env.example .env   # fill in DATABASE_URL
```

Bootstrap schema → [docs/setup.md](docs/setup.md).

### Web

```bash
cd web
pnpm install
```

No Python or database required for web work.

---

## Workspace layout

### Python (uv)

Marquise is a `uv` workspace (`[tool.uv.workspace] members = ["packages/*", "apps/*"]`).

| Member | Role | Console script |
|--------|------|----------------|
| `packages/marquise-core` | Domain library (importable as `marquise`) | — |
| `apps/marquise-api` | Read-only FastAPI REST API | `marquise-api` |
| `apps/marquise-cli` | Typer administration CLI | `marquise` |

Root `pyproject.toml` is **virtual** — no `[project]`/`[build-system]` table. It
holds workspace config, the shared `dev` dependency group, shared `ruff`/`ty`
config, and import-linter contracts. Each member owns its own `pyproject.toml`,
runtime dependencies, and pytest config.

**One lockfile rule**: only run `uv sync` / `uv lock` from the repo root, never
from inside a member directory.

**One version bump per package per PR**: combine all changes to an affected
package into one version increment and one changelog section.

### Bootstrap API

Apps in `apps/` access core through the public bootstrap API in
`packages/marquise-core/src/marquise/bootstrap.py`:

```python
from marquise import create_factory, create_factory_session

factory = await create_factory()
use_case = factory.list_cinemas_use_case
cinemas = await use_case.execute(use_case.InputData())

async with create_factory_session() as factory:
    use_case = factory.get_cinema_use_case
    result = await use_case.execute(use_case.InputData(cinema_id="..."))
```

### Public facade

Defined in `packages/marquise-core/src/marquise/__init__.py` via `__all__`:

- `MarquiseFactory`, `create_factory()`, `create_factory_session()`
- `ApplicationError` and concrete application exception subclasses
- Configured cinema, movie, screening, source, and import use cases required by delivery apps, including nested DTOs

Apps may import only from `marquise` (top-level) — never from
`marquise.domain`, `marquise.application`, `marquise.interface_adapters`, or
`marquise.infrastructure`.

**Enforcement:**

- AST scanner: `packages/marquise-core/tests/unit_tests/test_import_boundary.py`
- import-linter contract in root `pyproject.toml`
- Snapshot test: `packages/marquise-core/tests/unit_tests/test_public_api.py`

### Web (pnpm + Turborepo)

Self-contained under `web/`. Does not use uv or the Python workspace.

```
web/
├── package.json           # workspace root (private): turbo + shared scripts
├── pnpm-workspace.yaml    # apps/* and packages/*
├── turbo.json             # task pipeline
├── tsconfig.base.json     # shared TS strict defaults
├── apps/
│   └── marquise-interface/ # Vite + React app
└── packages/
    ├── marquise-client/   # client protocols, HTTP and mock clients
    └── components/         # marquise-components UI library
```

| Member | Role |
|--------|------|
| `packages/marquise-client` | Client protocols, API types, injected HTTP and mock implementations |
| `packages/components` | Publishable UI library (`marquise-components`); ships `dist/` + CSS bundle |
| `apps/marquise-interface` | Routes, client configuration, and UI composition |

**Install rule**: run `pnpm install` only from `web/`, never from a package subdirectory.

**Dependency rule**: apps → packages only. Packages must not import from apps.

**Public API**: consumers import via package `exports` (e.g. `marquise-components`, `marquise-components/index.css`). No deep imports into `src/` paths from outside the package.

**Dev-only code**: e.g. `packages/components/demo/` — local Vite demo, excluded from library build; never deploy.

### Web package roles

Design rules → [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md) and [web/README.md](web/README.md).

| Package | Role |
|---------|------|
| `packages/marquise-client` | Client protocols, API types, HTTP and mock implementations |
| `packages/components` | Publishable UI library (`marquise-components`); components and filter logic |
| `apps/marquise-interface` | Routes, client configuration, compose library exports |

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `CINEPLEX_API_KEY` | No | Cineplex API subscription key |
| `DATABASE_SCHEMA` | No | Schema name (default: `marquise`) |
| `MARQUISE_API_CACHE_TTL_SECONDS` | No | API in-memory cache TTL (default: 3600) |
| `MARQUISE_API_CORS_ORIGINS` | No | Comma-separated CORS origins (default: none) |
| `MARQUISE_API_RATE_LIMIT` | No | Per-IP rate limit, e.g. `60/minute` |
| `MARQUISE_API_LOG_LEVEL` | No | API log level (default: `INFO`) |

---

## Commands

### Makefile shortcuts

```bash
make test       # all 3 test suites
make test-core  # core unit tests
make test-api   # API tests
make test-cli   # CLI tests
make api        # API with hot reload
make cli        # CLI
make lint       # ruff check
make format     # ruff format
make ty         # type check marquise-core
```

### Manual equivalents

```bash
# Core unit tests (no DB)
uv run pytest packages/marquise-core/tests/unit_tests/ -q

# Single file or test name
uv run pytest packages/marquise-core/tests/unit_tests/domain/test_cinema.py -q
uv run pytest packages/marquise-core/tests/unit_tests/ -k "test_name" -q

# Core unit tests with coverage
uv run pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-report=term-missing -q

# Integration tests (requires DATABASE_URL in .env)
uv run pytest packages/marquise-core/tests/ -q

# App tests — one invocation per app (MarquiseFactory mocked, no DB)
uv run pytest apps/marquise-api/tests/ -q
uv run pytest apps/marquise-cli/tests/ -q

# Lint / format / type check
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .
uv run ruff format --check .
uv run ty check packages/marquise-core/src

# CLI / API
uv run marquise --help
uv run marquise-api

# Dependencies
uv add --package marquise-core <package>
uv add --package marquise-api <package>
uv add --package marquise-cli <package>
uv add --dev <package>
uv sync   # always from repo root
```

Never use `pip` directly — all Python dependencies go through `uv`.

### Web (from `web/`)

```bash
pnpm dev         # dev servers for all packages (turbo)
pnpm build       # build all packages in dependency order
pnpm lint        # oxlint across workspace
pnpm typecheck   # tsc --noEmit across workspace
pnpm test        # vitest across workspace

# Single package (example: components library + demo)
pnpm --filter marquise-components dev      # → http://localhost:5173
pnpm --filter marquise-components test
pnpm --filter marquise-components build
```

Add a dependency to one package:

```bash
pnpm --filter marquise-components add <package>
```

Never use `npm` or `yarn` in `web/` — pnpm only.

---

## Testability in this repo

Maps [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md) testability rules to concrete paths.

### Test layout

```
packages/marquise-core/tests/
├── conftest.py
├── unit_tests/
│   ├── domain/
│   ├── application/
│   └── interface_adapters/
└── integration_tests/
    └── infrastructure/    # real DB only

apps/marquise-api/tests/   # mock MarquiseFactory
apps/marquise-cli/tests/   # mock MarquiseFactory
```

No `integration_tests/interface_adapters/` — adapter tests are unit tests that
mock gateway protocols.

### What to mock where

| Code location | Test location | Mock |
|---------------|---------------|------|
| `domain/` | `unit_tests/domain/` | Nothing |
| `application/` | `unit_tests/application/` | Repository ABCs via `create_autospec` |
| `interface_adapters/` | `unit_tests/interface_adapters/` | Gateway protocols via `create_autospec` |
| `infrastructure/.../gateways/` | `integration_tests/infrastructure/` | Real database |
| `apps/marquise-api/` | `apps/marquise-api/tests/` | `MarquiseFactory` |
| `apps/marquise-cli/` | `apps/marquise-cli/tests/` | `MarquiseFactory` |

### Web

| Code location | Test location | Mock |
|---------------|---------------|------|
| `packages/components/src/**/*.tsx` | Colocated `*.test.tsx` | Mock `MovieGridClient` / `MovieDetailClient` or props; Testing Library |
| App routes/pages (when added) | Colocated or `apps/*/tests/` | Mock library client or API module |

Component tests use **Vitest** + **Testing Library**. No live HTTP in unit tests — implement a mock client protocol or pass data via props.

---

## CI pipeline

Pull requests to `main` run the repository workflows:

- `quality`: `ruff format --check`, `ruff check`, `ty check packages/marquise-core/src`, core unit tests with the 70% coverage gate, and the import boundary check.
- `integration`: `packages/marquise-core/tests/integration_tests/` with the configured `DATABASE_URL` secret.
- `release-validation`: release/package validation checks.

The exact trigger, command, and blocking behavior is defined by the workflow files in [`.github/workflows/`](.github/workflows/). In particular, `ty` is currently a blocking quality step; do not describe it as advisory here. The integration workflow is pull-request-triggered, not a manual-only job.

**CI gate**: 70% minimum. **Target**: 80%+ overall, 100% for `domain/` and
`application/`.

---

## Branch naming

- `feature/` or `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`

## Commit messages

Format: `type(scope): concise description`  
Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

## PR checklist

### Python changes

- [ ] `ruff format --check` and `ruff check` pass
- [ ] Unit tests pass (`pytest packages/marquise-core/tests/unit_tests/`)
- [ ] App tests pass if an app was touched
- [ ] Coverage did not drop below 70%
- [ ] Import boundary not violated
- [ ] Entry under current date in the affected package's `CHANGELOG.md` ([index](CHANGELOG.md)); version bump in affected package's `pyproject.toml`

### Web changes

- [ ] `pnpm lint`, `pnpm typecheck`, and `pnpm test` pass (from `web/`)
- [ ] Entry under current date in the affected package's `CHANGELOG.md` if user-facing ([index](CHANGELOG.md))
- [ ] No deep imports across package boundaries
- [ ] Dev-only demo code not included in library build output

### All changes

- [ ] Issue linked (`Closes #N`), or the PR body records the acceptance criteria for a trivial documentation/metadata change
- [ ] Independently reviewed under the [Code Review and Constructive Challenge](atlas/50-processes/Code%20Review%20and%20Constructive%20Challenge.md) process
- [ ] Clean Architecture check passes: inward dependencies, correct layer ownership, injectable collaborators, public facades/DTOs, and no unjustified abstraction or dependency
- [ ] Current-head CI is green and no blocking review thread remains unresolved

## Reporting issues

- **Bugs**: steps to reproduce, expected vs actual, Python version
- **Feature requests**: problem and proposed solution
- **Security**: private vulnerability report on GitHub — no public issues

## Further reading

### Delivery process

- [Atlas Documentation and Delivery Workflow](atlas/50-processes/Documentation%20and%20Delivery%20Workflow.md) — SSOT boundaries, briefs, stories, PRs, review, and verification gates
- [Project brief template](docs/templates/project-brief.md)
- [User story template](docs/templates/user-story.md)
- [Pull request template](.github/PULL_REQUEST_TEMPLATE.md)

### Documentation

- [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md) — layer diagram, DI, testability boundary
- [AGENTS.md](AGENTS.md) — enforced rules and agent context
- [docs/python.md](docs/python.md) — Python entity and use-case conventions
- [docs/setup.md](docs/setup.md) — database schema bootstrap
- [docs/sources.md](docs/sources.md) — showtime source scrapers
- [docs/releasing.md](docs/releasing.md) — version bumps and releases
- [web/README.md](web/README.md) — web workspace quick start
