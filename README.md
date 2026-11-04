# Marquise

Marquise aggregates Montreal cinema showtimes, normalizes them into PostgreSQL, and serves them through an admin CLI, public-read and authenticated-screening REST API, and React web interface.

- Live API: [marquise-api.fly.dev/docs](https://marquise-api.fly.dev/docs)

## Workspaces

| Workspace | Location | Tooling | Purpose |
|---|---|---|---|
| Python backend | repository root | [uv](https://docs.astral.sh/uv/) | Core library, FastAPI API, Typer CLI |
| Web frontend | `web/` | [pnpm](https://pnpm.io/) + [Turborepo](https://turbo.build/repo/docs) | React interface and shared packages |

The workspaces are independent. See [AGENTS.md](AGENTS.md#rules) for design rules and [CONTRIBUTING.md](CONTRIBUTING.md) for commands and CI.

## Setup

### Python backend

Requires Python 3.13 and uv.

```bash
git clone https://github.com/ArnaudJalbert/marquise.git
cd marquise
uv sync
cp .env.example .env   # set DATABASE_URL
```

### Web frontend

Requires Node.js ≥ 20 and pnpm 11.x.

```bash
cd web
corepack enable pnpm
pnpm install
pnpm dev
```

The web app defaults to mock data. For live data, run the backend and use `VITE_MARQUISE_DATA_SOURCE=api pnpm --filter marquise-interface dev`.

## Checks

From the repository root: `make test`, `make lint`, `make format`, and `make ty`.

From `web/`: `pnpm lint`, `pnpm typecheck`, `pnpm test`, and `pnpm build`.

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md): setup, commands, and CI
- [AGENTS.md](AGENTS.md): agent guide and rule index
- [docs/agents/rules/](docs/agents/rules/): architecture, Python, testing, web, and review rules
- [docs/](docs/): detailed setup, sources, release, and deployment notes
