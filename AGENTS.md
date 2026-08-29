# Development rules

Enforced standards for contributors and AI assistants.

| Document | Purpose |
|----------|---------|
| [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md) | Design principles: layers, DI, testability |
| [CONTRIBUTING.md](CONTRIBUTING.md) | This repository: setup, commands, paths, CI |
| [docs/](docs/) | Detailed repo-specific guidelines (read on demand) |

---

## Agent context

You are a **senior full-stack developer** working on this codebase.

**Priority order (non-negotiable):**

1. **Clean Architecture rules** — always win. Never break layer boundaries,
   dependency direction, injectability, or single responsibility to save lines.
   Lean means fewer lines *within* clean arch, not shortcuts around it.
2. **Lean / minimal (ponytail)** — default once arch constraints are satisfied.
   Prefer the smallest change that correctly solves the problem. Reuse before
   writing. Stdlib before dependencies. No speculative abstractions. Deletion
   over addition.

When lean and clean arch appear to conflict, choose clean arch and find a
smaller solution that still respects it — never the other way around.

When unsure, ship the simple version and note what was skipped. Complexity needs
justification; boredom is a feature — but architectural integrity is not optional.

---

## Monorepo contract

This repository contains **two independent monorepos**:

| Stack | Tooling | Scope |
|-------|---------|--------|
| Python backend | uv workspace | Library + API + CLI |
| Web frontend | pnpm workspace + Turborepo | Shared packages + apps |

They do not share a lockfile or package manager. Work in one subtree at a time.

### Python (uv)

- Shared library package + delivery app packages
- Virtual root workspace config; **single lockfile** — sync only from Python repo root
- Each member owns its own dependencies, scripts, and pytest config
- Run **each app test suite in its own pytest invocation**
- Delivery apps import the **library public facade only** (see [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md))

### Web (pnpm + Turborepo)

- Self-contained under `web/` — pnpm + Turborepo; single lockfile from `web/` root
- Apps → packages only; public API via package `exports`
- Inject client at boundary; no live HTTP in unit tests
- Full rules → [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md)

Repo-specific layout and commands → [CONTRIBUTING.md](CONTRIBUTING.md) (Python and web sections).

---

## Architecture contract

Details → [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md). **Clean Architecture is the ceiling
and the floor** — all work stays inside it. Ponytail optimisations must not
violate these rules:

- Inward dependencies only; single responsibility per component
- Infrastructure ↔ application boundary: **InputData / OutputData** at the
  delivery edge — no domain entities in delivery or infrastructure signatures
- **All collaborators injectable** at the composition root — no hidden globals,
  no constructing dependencies inside use cases

If a lean approach would skip a layer, merge boundaries, hard-code a dependency,
or expose domain types at the delivery edge, reject it and find a smaller change
that preserves the architecture.

---

## Testing contract

Everything through **interface adapters** is unit-testable with **zero external
I/O**. Infrastructure is the only layer that touches real externals (integration
tests only).

### Injectable dependencies

- Use cases receive repository interfaces via constructor — never instantiate stores inside
- Adapters receive gateway protocols via constructor — never open connections inside
- Controllers receive use cases via constructor
- Tests swap real collaborators for `create_autospec` mocks of the same ABC or protocol

Layer rules, testability boundary, and web testing →
[Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md).
Concrete test paths → [CONTRIBUTING.md#testability-in-this-repo](CONTRIBUTING.md#testability-in-this-repo).

### Mechanics

- Function-style tests — never class-based
- `@pytest.mark.asyncio` for async tests
- `create_autospec(Interface, instance=True)` — enforces signature match
- `assert_awaited_once()` / `assert_not_awaited()` for async mocks
- Scenario docstring on every test function
- Coverage: **70% CI minimum**; target **100%** for domain and application

### Red flags (reject in review)

- Use case that imports a DB driver, HTTP client, or reads env vars directly
- Application-layer test that hits a real database or network
- Module-level mutable container or cache
- Hard-coded dependency construction inside a use case or adapter
- Library component that fetches directly (no injected client or props)

---

### Python

- Complete type hints everywhere; `str | None` not `Optional`
- Never use `object`, `TypedDict`, or `Protocol` type hints; use plain `dict` at delivery formatting boundaries
- Entity / use-case conventions → [docs/python.md](docs/python.md)
- Ruff required before commit → [CONTRIBUTING.md](CONTRIBUTING.md)

### Web (TypeScript / React)

- Strict TypeScript; no `any` without a comment explaining why
- Prefer **props and injected dependencies** over module-level singletons (mirrors backend DI)
- Colocate tests next to source (`*.test.ts` / `*.test.tsx`); Testing Library — behaviour, not implementation
- Apps are thin: routing, inject real client, pass props to library components
- Full web rules → [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md)

---

## Violations checklist

Reject changes that:

- Break clean arch to save lines (skip injection, merge layers, domain types in delivery)
- Put business logic in delivery or controller
- Expose domain entities in infrastructure or delivery signatures
- Put SQL or HTTP in a use case or repository adapter
- Use non-injectable dependencies (constructed inside, global singleton)
- Require a live external service to test application logic
- Return raw dicts from repositories
- Import internal library layers from a delivery app
- **Web:** package importing from an app; deep-importing another package's internals; live API calls in unit tests; shipping dev-only demo code in library `dist`
- **Web:** library component fetching without injected client; app duplicating library UI instead of composing exports; client implementation outside a dedicated client package, or coupled to app routing or env

Rationale for each → [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md).

---

## Review contract

- AI-authored code requires review by a different person, Bot, or fresh temporary reviewer.
- Reviews lead with the strongest material objection, if one exists; otherwise they state what they tried to falsify and the residual risk. Use tests, measurements, code, or documented constraints as evidence.
- Authors evaluate feedback rather than accepting it reflexively; reviewers withdraw findings disproved by evidence.
- Unresolved routine technical disagreements go to Aster. Product direction, major architecture, irreversible migrations, security posture, cost, and priority go to Arno.
- Full workflow: [Code Review and Constructive Challenge](atlas/50-processes/Code%20Review%20and%20Constructive%20Challenge.md).

---

## Detailed guidelines

Repo-specific detail lives in `docs/` — read when the task touches that area:

| Guideline | When to read |
|-----------|--------------|
| [Atlas Clean Architecture](atlas/50-processes/Clean%20Architecture.md) | Layer boundaries, DI, testability, web package design |
| [docs/python.md](docs/python.md) | Domain entities, value objects, use cases |
| [docs/setup.md](docs/setup.md) | Database setup, schema, Supabase |
| [docs/sources.md](docs/sources.md) | Scrapers, source adapters, registry |
| [docs/releasing.md](docs/releasing.md) | Version bumps, tags, releases |
