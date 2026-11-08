# Contributing to Marquise

Repository setup, commands, paths, and CI. Rules for code, tests, and PRs live in
[docs/agents/rules/](docs/agents/rules/), indexed from [AGENTS.md](AGENTS.md#rules).

---

## Prerequisites

**Python backend**

- Python 3.13
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

**Web frontend** (only if working in `web/`)

- [Node.js](https://nodejs.org/) `^22.13.0 || >=24.0.0`, the range pnpm 11, Vite and jsdom all support (CI uses 24, the production image 22)
- [pnpm](https://pnpm.io/) 11 via Corepack (`corepack enable pnpm`); the exact version is pinned in `web/package.json`

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
| `apps/marquise-api` | Public reads and authenticated screening FastAPI REST API | `marquise-api` |
| `apps/marquise-cli` | argparse administration CLI (`cinema`, `source`, `import`, `movie`, `auth`) | `marquise` |

Root `pyproject.toml` is **virtual** — no `[project]`/`[build-system]` table. It
holds workspace config, the shared `dev` dependency group, and shared `ruff`/`ty`
config. Each member owns its own `pyproject.toml`,
runtime dependencies, and pytest config.

Apps reach core only through the `marquise` facade; see the
[architecture rules](docs/agents/rules/architecture.md#public-facade).

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

Package roles and dependency rules: [web rules](docs/agents/rules/web.md).

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SUPABASE_URL` | Protected API routes and account CLI | HTTPS Supabase project URL; userinfo, query strings, and fragments are rejected |
| `MARQUISE_AUTH_ALLOW_LOCAL_HTTP` | No | Set exactly `1` for local development HTTP using a literal loopback IP (`127.0.0.1` or `::1`); hostnames and remote HTTP remain forbidden |
| `SUPABASE_PUBLISHABLE_KEY` | Account CLI only | Password authentication for Administrator verification |
| `SUPABASE_SERVICE_ROLE_KEY` | Account CLI only | Privileged invitation and role metadata updates |
| `MARQUISE_EMAIL` | No | Configured CLI Administrator email; prompts when either credential is absent |
| `MARQUISE_PASSWORD` | No | Configured CLI Administrator password; prompts when either credential is absent |
| `CINEPLEX_API_KEY` | No | Cineplex API subscription key |
| `TMDB_API_KEY` | Imports | TMDB API key for matching movies during import; imports fail if it is absent |
| `DATABASE_SCHEMA` | No | Schema name (default: `marquise`) |
| `MARQUISE_API_CACHE_TTL_SECONDS` | No | API in-memory cache TTL (default: 3600) |
| `MARQUISE_API_CORS_ORIGINS` | No | Comma-separated CORS origins (default: none) |
| `MARQUISE_API_RATE_LIMIT` | No | Per-IP rate limit (default: `3000/minute`) |
| `MARQUISE_API_LOG_LEVEL` | No | API log level (default: `INFO`) |
| `SOURCE_DATABASE_URL`, `TARGET_DATABASE_URL` | `scripts/transfer_cinema_configuration.py` only | Source and destination of the cinema configuration transfer ([fly-postgres.md](docs/fly-postgres.md)) |
| `VITE_MARQUISE_API_BASE_URL` | No (web) | API origin for the interface build (default: same origin; the Docker build sets `https://api.marquise.mov`) |
| `VITE_MARQUISE_DATA_SOURCE` | No (web) | Demo only: `api` makes `pnpm prototype` call the API instead of sample data |

Importing `marquise.infrastructure.di.container` runs `load_dotenv()`, so a local
`.env` leaks into any process or test that builds the factory.

---

## Commands

### Makefile shortcuts

```bash
make test                    # core, API and CLI test suites
make test-core               # core unit tests
make test-core-integrations  # core integration tests (disposable PostgreSQL DATABASE_URL)
make test-api                # API tests
make test-cli                # CLI tests
make api                     # API with hot reload on :8000
make cli                     # CLI
make lint                    # ruff check
make format                  # ruff format
make ty                      # type check marquise-core
make web                     # interface dev server; /v1 proxies to a local API on :8000
make web-live                # local API and interface together
make web-demo                # sample-data component demo (pnpm prototype)
make local-up                # isolated Postgres + API + built app, see local/README.md
make deploy-api              # Fly deploy, also run by CI
make deploy-interface        # Fly deploy, also run by CI
```

### Manual equivalents

```bash
# Core unit tests (no DB)
uv run pytest packages/marquise-core/tests/unit_tests/ -q

# Single file or test name
uv run pytest packages/marquise-core/tests/unit_tests/domain/entities/test_cinema.py -q
uv run pytest packages/marquise-core/tests/unit_tests/ -k "test_name" -q

# Core unit tests with coverage
uv run pytest packages/marquise-core/tests/unit_tests/ --cov=marquise --cov-report=term-missing -q

# Deterministic integration tests (requires a disposable PostgreSQL DATABASE_URL)
uv run pytest packages/marquise-core/tests/integration_tests/ -q

# Live provider connectivity only (requires internet, no database)
uv run pytest packages/marquise-core/tests/provider_smoke_tests/ -q

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

### Web (from `web/`)

```bash
pnpm dev         # interface dev server (the only package with a dev script)
pnpm build       # build all packages in dependency order
pnpm lint        # oxlint across workspace
pnpm typecheck   # tsc --noEmit across workspace
pnpm test        # vitest across workspace

pnpm prototype   # sample-data component demo → http://localhost:4174

# Single package
pnpm --filter marquise-components test
pnpm --filter marquise-components build
```

Add a dependency to one package:

```bash
pnpm --filter marquise-components add <package>
```

---

## Test layout

What to mock in each layer: [testing rules](docs/agents/rules/testing.md).


```
packages/marquise-core/tests/
├── unit_tests/
│   ├── domain/
│   ├── application/          # includes test_use_case_architecture.py
│   ├── interface_adapters/
│   ├── infrastructure/       # DI and gateways with fake transports
│   ├── security/
│   ├── test_import_boundary.py
│   └── test_public_api.py
├── integration_tests/        # disposable PostgreSQL; conftest.py here
│   └── infrastructure/
├── provider_smoke_tests/     # live provider connectivity
├── fixtures/
└── support/

apps/marquise-api/tests/      # mock MarquiseFactory
apps/marquise-cli/tests/      # mock MarquiseFactory
```

Web tests are colocated with their source as `*.test.ts` / `*.test.tsx`.

---

## CI pipeline

Pull requests to `main` run the repository workflows:

- `quality`: `ruff format --check`, `ruff check`, `ty check packages/marquise-core/src`, core unit tests with the 70% coverage gate, API and CLI tests, and the deterministic integration suite against a disposable PostgreSQL 17 service. The core unit tests include the architecture tests (`test_import_boundary.py`, `test_public_api.py`, `test_use_case_architecture.py`).
- `release-validation`: when a package's `src/**` or `pyproject.toml` changes, its version must increase, and its distributions must build.
- `web-quality`: for web changes, install the frozen pnpm workspace and run web lint, TypeScript checks, unit tests, and production builds on Node.js 24.

The nightly `integration` workflow runs the same deterministic suite against its own PostgreSQL 17 service. It needs no production secrets or live provider access. The separate `provider-connectivity` workflow checks the real Cineplex and CinemaCinema endpoints daily and by manual dispatch. Its failures are visible but do not fail the deterministic suite; a connectivity check does not validate every showtime or movie-detail response.

After merge and on schedule:

- `release`: on push to `main`, tags and releases each bumped package ([docs/releasing.md](docs/releasing.md)).
- `fly-deploy`: on push to `main` touching deployable paths, deploys the API and interface to Fly and smoke-tests them ([docs/deployment.md](docs/deployment.md)).
- `scheduled-import`: daily import into Supabase; manual dispatch imports into Fly `marquise-db` ([docs/fly-postgres.md](docs/fly-postgres.md)).

Triggers, commands and environment wiring are defined in [`.github/workflows/`](.github/workflows/). `ty` is a blocking quality step.

Coverage gate and targets: [testing rules](docs/agents/rules/testing.md#coverage).

---

Branch and commit conventions: [review and delivery rules](docs/agents/rules/review-and-delivery.md#branches-and-commits).

## PR checklist

### Python changes

- [ ] `ruff format --check` and `ruff check` pass
- [ ] Unit tests pass (`pytest packages/marquise-core/tests/unit_tests/`)
- [ ] App tests pass if an app was touched
- [ ] Coverage did not drop below 70%
- [ ] Version bump in affected package's `pyproject.toml`

### Web changes

- [ ] `pnpm lint`, `pnpm typecheck`, and `pnpm test` pass (from `web/`)

### All changes

- [ ] The change follows the matching [rules](AGENTS.md#rules), including [review and delivery](docs/agents/rules/review-and-delivery.md)

## Reporting issues

- **Bugs**: steps to reproduce, expected vs actual, Python version
- **Feature requests**: problem and proposed solution
- **Security**: private vulnerability report on GitHub — no public issues

## Further reading

- [AGENTS.md](AGENTS.md): rule index and guide index
- [Pull request template](.github/PULL_REQUEST_TEMPLATE.md)

### Authentication transport

GoTrue credential-bearing requests reject redirects, including same-origin redirects.
Configure the final HTTPS endpoint directly. TLS certificate verification remains enabled.
The configured JWKS URL also requires HTTPS (or the explicit loopback development opt-in).
This does not configure inbound API HTTPS; enforce that at the deployment proxy.

## Isolated local integration stack

Run `make local-up` to build and start a local Postgres database, real API, and
React app at `http://localhost:4300`. No production environment files or services
are required. The database contains controlled test schedules. See
[local/README.md](local/README.md) for data, ports, rebuild/reseed/stop commands and
the real HTTP/browser verification script.
