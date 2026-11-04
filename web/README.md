# Marquise Web

The new front-end workspace for Marquise (recreated after the old `web/` monorepo was
removed in `2c1f93e` to start the UI from scratch). A [pnpm workspace](https://pnpm.io/workspaces)
orchestrated by [Turborepo](https://turbo.build/repo/docs), living alongside the Python
backend in the same repository.

> You do not need Python, `uv`, or a database to work here. This subtree is self-contained —
> the only prerequisites are Node.js and pnpm. See [web rules](../docs/agents/rules/web.md) for
> rules and [CONTRIBUTING.md](../CONTRIBUTING.md) for paths and commands.

## Minimalist browsing

The production app uses the approved shared minimalist UI against the real API.
`/` opens today's Montreal Screenings. `/?section=movies` searches the independent
catalogue. Both views load bounded pages and append the next page on scroll. Cinema
directory and venue pages use real data. Movie links
resolve metadata by exact ID and load the requested schedule window.

The approved sample prototype stays in `packages/components/demo`, outside the
production bundle. Run `pnpm prototype` for it. See
[design/332/README.md](design/332/README.md) for its data and historical evidence.

## Design

Package roles and design rules: [web rules](../docs/agents/rules/web.md).

## Layout

```
web/
├── package.json          # Workspace root (private): Turborepo + shared scripts
├── pnpm-workspace.yaml   # Declares the workspaces: apps/* and packages/*
├── turbo.json            # Task pipeline (build, dev, lint, typecheck, test)
├── apps/
│   └── marquise-interface/  # Discovery, daily screenings, cinemas, films (Vite + React + TS)
└── packages/
    ├── marquise-client/  # REST API + mock data clients
    └── components/       # marquise-components — self-contained component library
```

## Prerequisites

| Tool | Version |
|---|---|
| [Node.js](https://nodejs.org/) | `^22.13.0 \|\| >=24.0.0` (CI uses 24, the production image 22) |
| [pnpm](https://pnpm.io/) | 11, pinned in `package.json`, via Corepack |

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

# The production interface, using the real API:
pnpm --filter marquise-interface dev
# → http://localhost:5173

# Same-origin /v1/* requests proxy to http://localhost:8000. Run `make api`.
# For another API origin, set VITE_MARQUISE_API_BASE_URL at build/dev time.
```

## API and production builds

- The injected `BrowseClient` separates `GET /v1/screening-movies` from
  `GET /v1/movies`. Screening pages contain 24 distinct movies, ordered by the
  earliest upcoming show and ID, plus at most three qualifying screenings each.
  Catalogue pages contain 24 movies and accept an endpoint title search without
  screening constraints. Both expose authoritative totals and page counts.
- Movie routes use `GET /v1/movies?ids=<encoded-id>&size=1` and the existing exact-ID
  screening endpoint for inclusive Montreal date windows. Metadata and booking
  URLs remain real. Missing posters, metadata, and booking links have plain
  fallbacks. API failures show Retry and never substitute sample data.
- The default client always uses HTTP. Docker defaults the API origin to
  `https://api.marquise.mov`; other builds use same-origin requests unless
  `VITE_MARQUISE_API_BASE_URL` is supplied. The older client interfaces remain
  available to independent consumers.
- The shared package ships `dist/index.css`. Workspace development resolves the
  component code and stylesheet from source. The demo stays outside library
  output; the library build fails if demo fixtures reach `dist/`.
- Static hosting must rewrite document requests to `index.html` for movie links,
  refreshes, and cinema routes.
- On constrained hosts, use `pnpm lint -- --threads=2` and
  `pnpm test -- --maxWorkers=2`.
