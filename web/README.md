# Marquise Web

The new front-end workspace for Marquise (recreated after the old `web/` monorepo was
removed in `2c1f93e` to start the UI from scratch). A [pnpm workspace](https://pnpm.io/workspaces)
orchestrated by [Turborepo](https://turbo.build/repo/docs), living alongside the Python
backend in the same repository.

> You do not need Python, `uv`, or a database to work here. This subtree is self-contained —
> the only prerequisites are Node.js and pnpm.

## Layout

```
web/
├── package.json          # Workspace root (private): Turborepo + shared scripts
├── pnpm-workspace.yaml   # Declares the workspaces: apps/* and packages/*
├── turbo.json            # Task pipeline (build, dev, lint, typecheck, test)
├── apps/
│   └── marquise-interface/  # The Marquise landing page (Vite + React + TS)
└── packages/
    ├── marquise-client/  # REST API + mock data clients
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
pnpm dev        # landing page with source HMR for both workspace packages
pnpm build      # build every package in dependency order
pnpm lint       # oxlint across the workspace
pnpm typecheck  # tsc --noEmit across the workspace
pnpm test       # vitest across the workspace

# The landing page (mock data by default):
pnpm --filter marquise-interface dev
# → http://localhost:5173

# Use live API data (proxies /v1/* to http://localhost:8000 — run `make api`):
VITE_MARQUISE_DATA_SOURCE=api pnpm --filter marquise-interface dev
```

## Notes

- `packages/components` ships a **prebuilt CSS bundle** (`dist/index.css`), so external
  consumers do not need their own Tailwind install. The workspace app resolves both the
  component code and stylesheet from source for fresh-checkout development and HMR.
- `marquise-interface` is the development and visual-test consumer for the shared component
  package; there is no second demo application to keep in sync.
- `marquise-interface` uses client-side movie routes such as `/movies/<id>`. Production
  static hosting must rewrite unknown document requests to `index.html` so direct movie
  links and refreshes load the Vite app.
