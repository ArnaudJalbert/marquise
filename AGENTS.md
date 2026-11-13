# Marquise agent guide

Montreal cinema showtimes: a Python backend (uv workspace: `packages/marquise-core`, `apps/marquise-api`, `apps/marquise-cli`) and a web frontend (`web/`, pnpm and Turborepo). The two share no lockfile or package manager; work in one subtree at a time.

## Priorities

1. **Clean Architecture wins.** Layer boundaries, inward dependencies, injectable collaborators and single responsibility hold on every change.
2. **Then ponytail.** The smallest change that fully solves the task: reuse first, stdlib before dependencies, deletion over addition, abstractions only with a concrete payoff. Ponytail never trades away safety, correctness, data integrity, acceptance criteria or required tests; a shorter diff is not automatically better.

When they pull apart, keep the architecture and find a smaller change inside it. When unsure, ship the simple version and say what was skipped.

The shared coding standards below take precedence over ponytail, and Marquise's own rules take precedence over them.

## Shared coding standards

This repo follows the Calepin `coding-clean-architecture` and `coding-use-cases` standards, plus the always-on `coding-functions`, `coding-naming`, `coding-python` and `coding-testing`. Load each skill before the work it names. They live in the Calepin vault under `90-agents/skills/coding-*`, and each routes to its note in `30-zettelkasten/` (map: `Coding standards.md`). The rule files below hold only what is specific to Marquise.

| Skill | Read when |
|---|---|
| `coding-clean-architecture` | Adding a use case, repository, gateway, adapter or endpoint; moving code across layers; wiring dependencies; changing what apps import |
| `coding-use-cases` | Creating, changing, reviewing or testing a use case or query |
| `coding-functions` | Writing or reviewing functions and methods |
| `coding-naming` | Naming or reviewing variables, parameters, properties, functions, classes, types, or components |
| `coding-python` | Writing or reviewing Python, including docstrings |
| `coding-testing` | Writing, moving or reviewing tests |

## Rules

Read the matching file before the work it names. How rules are written and added: [docs/agents/rules/README.md](docs/agents/rules/README.md).

| Rules | Read when |
|---|---|
| [architecture](docs/agents/rules/architecture.md) | Adding a use case, repository, gateway, adapter or endpoint; moving code across layers; wiring dependencies; changing what apps import. Layer paths and the `marquise` facade |
| [python](docs/agents/rules/python.md) | Writing or reviewing Python: error locations, uv lockfile, quality gate |
| [testing](docs/agents/rules/testing.md) | Writing, moving or reviewing tests: test locations, `new_tests/` transition, coverage gate |
| [web](docs/agents/rules/web.md) | Working under `web/` |
| [enforcement](docs/agents/rules/enforcement.md) | Adding a rule or check; deciding what to verify at each stage |
| [review-and-delivery](docs/agents/rules/review-and-delivery.md) | Filing an issue; opening, reviewing or merging a PR |

## Guides

| Guide | Read when |
|---|---|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setting up, running commands, checking CI |
| [docs/setup.md](docs/setup.md) | Database schema, migrations |
| [docs/sources.md](docs/sources.md) | Scrapers, source adapters, the source registry |
| [docs/metadata-contracts.md](docs/metadata-contracts.md), [docs/providers/tmdb-metadata.md](docs/providers/tmdb-metadata.md) | Movie metadata and TMDB |
| [docs/merge-movies.md](docs/merge-movies.md) | Merging duplicate movies |
| [docs/releasing.md](docs/releasing.md) | Version bumps, tags, releases |
| [docs/deployment.md](docs/deployment.md) | Deploying, scheduled imports |
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
