# Contributing to Marquise

## Prerequisites

- **Python 3.13+** — verify with `python --version`
- **uv** — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

```bash
git clone https://github.com/arnaudjalbert/marquise.git
cd marquise
uv sync
cp .env.example .env          # fill in SUPABASE_URL, SUPABASE_KEY, DATABASE_URL
```

## Day-to-day commands

```bash
# Unit tests (no DB required)
uv run pytest tests/unit_tests/ -q

# All tests (requires Supabase credentials in .env)
uv run pytest tests/ -q

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Run the CLI
uv run marquise --help
```

## CI pipeline

Every push and pull request to `main` runs:

1. `ruff format --check` — formatting check
2. `ruff check` — linting
3. `pytest --cov --cov-fail-under=80` — unit tests with **80% coverage gate**

Integration tests (require Supabase secrets) run on manual trigger only.

> **Coverage**: The CI gate is **80% minimum**. The target for `domain/` and `application/` layers is 100% — do not add uncovered lines in these layers without a strong reason.

## Architecture overview

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details. Quick summary — four layers, dependencies point inward only:

| Layer | Location | Responsibility |
|---|---|---|
| Domain | `src/marquise/domain/` | Entities, value objects — no external deps |
| Application | `src/marquise/application/` | Use cases, repository ABCs |
| Interface adapters | `src/marquise/interface_adapters/` | Repository implementations, source adapters |
| Infrastructure | `src/marquise/infrastructure/` | CLI, Supabase gateways, DI container |

## Branch naming

- `feature/short-description`
- `fix/short-description`
- `docs/short-description`
- `refactor/short-description`

## Commit messages

Format: `type(scope): concise description`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Examples:
- `feat(domain): add Promotion entity with validation`
- `fix(import): correct updated_count docstring`
- `docs: rewrite AGENTS.md to match current architecture`

## PR checklist

- [ ] Tests pass: `uv run pytest tests/unit_tests/ -q`
- [ ] Lint clean: `uv run ruff check src/ tests/`
- [ ] Format clean: `uv run ruff format --check src/ tests/`
- [ ] `CHANGELOG.md` entry added
- [ ] Version bumped in `pyproject.toml` (semver: patch / minor / major)
- [ ] Issue linked in PR description

## Reporting issues

- **Bugs**: include steps to reproduce, expected vs actual behavior, environment
- **Feature requests**: describe the problem you're solving and proposed solution
- **Security issues**: open a private security advisory on GitHub (do not open public issues)
