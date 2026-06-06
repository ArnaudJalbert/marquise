# Contributing to Marquise

Thank you for your interest in contributing to Marquise! This document provides a quick overview of how to get started. For detailed, authoritative development guidelines, **please read [AGENTS.md](AGENTS.md)** first - it contains everything you need to know about architecture, standards, and workflows.

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/anomalyco/marquise.git
cd marquise

# Install dependencies and create virtual environment
uv sync

# Verify setup
uv run python --version  # Should show Python 3.13.x
```

### Development Workflow

1. **Pull latest changes** before starting work
2. **Make focused, small changes** - one feature/fix at a time
3. **Format and lint** after each change:
   ```bash
   uv run ruff format .
   uv run ruff check --fix
   ```
4. **Run tests with coverage**:
   ```bash
   uv run pytest tests/ --cov=domain --cov=application --cov=interface_adapters --cov-report=term-missing
   ```
5. **Ensure 100% coverage** on domain, application, and interface_adapters layers
6. **Commit with a clear message** following conventional commits format

## Project Architecture

Marquise uses **Clean Architecture** with four layers:

```
domain/          - Business logic, entities, value objects, repository interfaces
application/     - Use cases that orchestrate domain objects
interface_adapters/ - FastAPI routes, DTOs, controllers
infrastructure/  - MongoDB implementations, external integrations
```

**Key rule**: Dependencies point inward only. Domain knows nothing about databases or HTTP. See [AGENTS.md](AGENTS.md#4-clean-architecture-the-foundation) for complete details.

## Code Standards

- **Type hints**: Required on all functions, arguments, and return types
- **Async-first**: All I/O operations should be async
- **Testing**: 100% coverage required for core layers (domain, application, interface_adapters)
- **Style**: Automated with ruff (formatting + linting)

See [AGENTS.md](AGENTS.md#6-code-quality-standards) for full standards.

## Reporting Issues

- **Bug reports**: Please include steps to reproduce, expected vs actual behavior, environment details
- **Feature requests**: Describe the problem you're solving and proposed solution
- **Security issues**: Email security@anomaly.co (do not open public issues)

## Code Review Process

1. All changes require code review
2. Reviewers will check: architecture compliance, test coverage, code quality, documentation
3. Address all review comments before merge
4. Squash commits for clean history (follow-up: amend is okay for small fixes)

## Questions?

- **Detailed guidelines**: Read [AGENTS.md](AGENTS.md) - it's comprehensive and prescriptive
- **Architecture questions**: See Clean Architecture section in AGENTS.md
- **Testing questions**: See Testing Strategy in AGENTS.md
- **API questions**: See REST API Development in AGENTS.md

## License

[Insert license information here]

---

**Note**: This CONTRIBUTING.md is a brief overview. [AGENTS.md](AGENTS.md) is the authoritative, detailed guide that all developers **must** follow. Always consult AGENTS.md before making code changes.
