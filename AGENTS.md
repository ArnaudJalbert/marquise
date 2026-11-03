# Marquise agent guide

Montreal cinema showtimes: a Python backend (uv workspace: `packages/marquise-core`, `apps/marquise-api`, `apps/marquise-cli`) and a web frontend (`web/`, pnpm and Turborepo). The two share no lockfile or package manager; work in one subtree at a time.

## Priorities

1. **Clean Architecture wins.** Layer boundaries, inward dependencies, injectable collaborators and single responsibility hold on every change.
2. **Then ponytail.** The smallest change that fully solves the task: reuse first, stdlib before dependencies, deletion over addition, abstractions only with a concrete payoff.

When they pull apart, keep the architecture and find a smaller change inside it. When unsure, ship the simple version and say what was skipped.

## Rules

Read the matching file before the work it names. How rules are written and added: [docs/agents/rules/README.md](docs/agents/rules/README.md).

| Rules | Read when |
|---|---|
| [architecture](docs/agents/rules/architecture.md) | Adding or moving Python code across layers, wiring dependencies, changing what apps import |
| [python](docs/agents/rules/python.md) | Writing or reviewing Python |
| [testing](docs/agents/rules/testing.md) | Writing, moving or reviewing tests |
| [web](docs/agents/rules/web.md) | Working under `web/` |
| [review-and-delivery](docs/agents/rules/review-and-delivery.md) | Opening, reviewing or merging a PR |

## Guides

| Guide | Read when |
|---|---|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setting up, running commands, checking CI |
| [docs/setup.md](docs/setup.md) | Database schema, migrations, Supabase Auth |
| [docs/sources.md](docs/sources.md) | Scrapers, source adapters, the source registry |
| [docs/metadata-contracts.md](docs/metadata-contracts.md), [docs/providers/tmdb-metadata.md](docs/providers/tmdb-metadata.md) | Movie metadata and TMDB |
| [docs/merge-movies.md](docs/merge-movies.md) | Merging duplicate movies |
| [docs/releasing.md](docs/releasing.md) | Version bumps, changelogs, tags |
| [docs/deployment.md](docs/deployment.md), [docs/fly-postgres.md](docs/fly-postgres.md) | Deploying, Fly Postgres, scheduled imports |
| [docs/privacy-operations.md](docs/privacy-operations.md) | Personal data handling |
| [local/README.md](local/README.md) | The isolated local stack (`make local-up`) |
| [web/README.md](web/README.md) | Web workspace quick start |

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `ArnaudJalbert/marquise`. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses mapped GitHub labels plus `type:*` and `area:*` category labels. See `docs/agents/triage-labels.md`.

### Domain docs

Domain documentation uses a multi-context layout. See `docs/agents/domain.md`.
