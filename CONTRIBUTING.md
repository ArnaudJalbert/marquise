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

## Day-to-day commands

```bash
# Run unit tests (no DB required)
uv run pytest tests/unit_tests/ -q

# Run all tests including integration (requires Supabase credentials)
uv run pytest tests/ -q

# Run unit tests with coverage
uv run pytest tests/unit_tests/ --cov=marquise --cov-report=term-missing -q

# Lint
uv run ruff check src/ tests/

# Auto-fix lint
uv run ruff check --fix src/ tests/

# Type check (non-blocking in CI for now)
uv run ty check src

# Format
uv run ruff format src/ tests/

# Check formatting without modifying (what CI runs)
uv run ruff format --check src/ tests/

# Explore the CLI
uv run marquise --help
```

## CI pipeline

Every push and PR to `main` runs the `quality` job:

1. `ruff format --check` — fails on unformatted code
2. `ruff check` — fails on lint errors
3. `ty check src` — type check; **non-blocking** for now (reports diagnostics without failing the build while the backlog is triaged, see #34)
4. `pytest tests/unit_tests/ --cov=marquise --cov-fail-under=70` — fails below 70% coverage

The `integration` job (manual trigger only) runs `tests/integration/` using secrets `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL`.

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
- [ ] Unit tests pass (`pytest tests/unit_tests/`)
- [ ] Coverage did not drop below 70%
- [ ] `CHANGELOG.md` entry added
- [ ] Version bumped in `pyproject.toml` (semver: major/minor/patch)
- [ ] Issue linked in PR body (`Closes #N`)

## Reporting issues

- **Bugs**: include steps to reproduce, expected vs actual behaviour, Python version
- **Feature requests**: describe the problem and proposed solution
- **Security issues**: open a private vulnerability report on GitHub (do not open public issues)

## Architecture overview

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full layer diagram and key patterns.  
See [AGENTS.md](AGENTS.md) for development rules and coding standards.
