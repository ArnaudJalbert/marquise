# Marquise

Marquise aggregates Montreal cinema showtimes, normalizes them into PostgreSQL, and exposes the data through an administration CLI, a read-only REST API, and a React web interface.

- Live API: [marquise-api.fly.dev/docs](https://marquise-api.fly.dev/docs)
- Repository: [ArnaudJalbert/marquise](https://github.com/ArnaudJalbert/marquise)
- Company knowledge and operating processes: [Marquise Atlas](atlas/README.md)

## Architecture and workspaces

This repository contains two independent workspaces. Work in one subtree at a time; they do not share a package manager or lockfile.

| Workspace | Location | Tooling | Purpose |
|---|---|---|---|
| Python backend | repository root | [uv](https://docs.astral.sh/uv/) | `marquise-core` domain/application library, FastAPI API, Typer CLI |
| Web frontend | `web/` | [pnpm](https://pnpm.io/) + [Turborepo](https://turbo.build/repo/docs) | React interface and shared client/components packages |

The backend follows Clean Architecture: delivery → infrastructure → interface adapters → application → domain. The web apps compose package exports; packages do not import apps. See [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md) for the canonical design rules and [docs/architecture.md](docs/architecture.md) for the repository pointer.

## Local setup

### Python backend

Prerequisites: Python 3.13 and uv.

```bash
git clone https://github.com/ArnaudJalbert/marquise.git
cd marquise
uv sync
cp .env.example .env   # set DATABASE_URL
```

Schema and database setup: [docs/setup.md](docs/setup.md). The root `pyproject.toml` is a virtual uv workspace; run `uv sync` only from the repository root.

### Web frontend

Prerequisites: Node.js ≥ 20 and pnpm 11.x.

```bash
cd web
corepack enable pnpm
pnpm install
pnpm dev
```

The web workspace is self-contained and defaults to mock data. For live API data, run the backend and use `VITE_MARQUISE_DATA_SOURCE=api pnpm --filter marquise-interface dev`. See [web/README.md](web/README.md).

## Common checks

From the repository root:

```bash
make test
make lint
make format
make ty
```

For web checks, from `web/`: `pnpm lint`, `pnpm typecheck`, `pnpm test`, and `pnpm build`. Exact commands, test paths, environment variables, and CI behavior live in [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation and contribution

- [CONTRIBUTING.md](CONTRIBUTING.md) — setup, workspace layout, commands, CI, and PR checklist
- [AGENTS.md](AGENTS.md) — enforced developer and AI-assistant rules
- [Atlas README](atlas/README.md) — company knowledge-base boundaries and navigation
- [Atlas Documentation and Delivery Workflow](atlas/50-processes/Documentation%20and%20Delivery%20Workflow.md) — SSOT, briefs, stories, PRs, reviews, and gates
- [docs/](docs/) — detailed backend, setup, source, release, and deployment notes
