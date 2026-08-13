# Marquise Web

The new front-end workspace for Marquise (recreated after the old `web/` monorepo was
removed in `2c1f93e` to start the UI from scratch). A [pnpm workspace](https://pnpm.io/workspaces)
orchestrated by [Turborepo](https://turbo.build/repo/docs), living alongside the Python
backend in the same repository.

> You do not need Python, `uv`, or a database to work here. This subtree is self-contained —
> the only prerequisites are Node.js and pnpm. See [AGENTS.md](../AGENTS.md) for enforced
> rules and [CONTRIBUTING.md](../CONTRIBUTING.md) for paths and commands.

## Design

- **`marquise-components`** is modular and self-contained: presentational UI, pure filter logic, and **client protocol interfaces** (`MovieGridClient`, `MovieDetailClient`) exported from the package
- **Apps compose** library exports — routes, layout, and real API wiring live in apps, not in the library
- **Client implementations** are generic interfaces in the package; apps provide concrete fetch logic and pass them via the `client` prop
- Each package builds, lints, typechecks, and tests on its own (demo uses a mock client; no app required)

Full rules → [docs/architecture.md](../docs/architecture.md) (modular web packages) and [AGENTS.md](../AGENTS.md).

## Layout

```
web/
├── package.json          # Workspace root (private): Turborepo + shared scripts
├── pnpm-workspace.yaml   # Declares the workspaces: apps/* and packages/*
├── turbo.json            # Task pipeline (build, dev, lint, typecheck, test)
├── apps/                 # Runnable applications (empty until one ships)
└── packages/
    └── components/       # marquise-components — self-contained component library
```

## Prerequisites

| Tool | Version |
|---|---|
| [Node.js](https://nodejs.org/) | ≥ 20 (developed on 26) |
| [pnpm](https://pnpm.io/) | 11.x — provisioned via Corepack |

```bash
corepack enable pnpm
```

## Getting started

All commands run from the `web/` directory.

```bash
pnpm install
```

## Everyday commands

```bash
pnpm dev        # dev servers for every package (currently: the components demo page)
pnpm build      # build every package in dependency order
pnpm lint       # oxlint across the workspace
pnpm typecheck  # tsc --noEmit across the workspace
pnpm test       # vitest across the workspace

# The components demo page (dev-only, never deployed):
pnpm --filter marquise-components dev
# → http://localhost:5173
```

## Notes

- `packages/components` ships a **prebuilt CSS bundle** (`dist/index.css`), so consumers do
  not need their own Tailwind install.
- The `demo/` page inside `packages/components` is excluded from the library build and is
  dev-only — it never lands in `dist/` and must never be deployed.
