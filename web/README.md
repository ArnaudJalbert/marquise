# Marquise Web

The new front-end workspace for Marquise (recreated after the old `web/` monorepo was
removed in `2c1f93e` to start the UI from scratch). A [pnpm workspace](https://pnpm.io/workspaces)
orchestrated by [Turborepo](https://turbo.build/repo/docs), living alongside the Python
backend in the same repository.

> You do not need Python, `uv`, or a database to work here. This subtree is self-contained —
> the only prerequisites are Node.js and pnpm. See [AGENTS.md](../AGENTS.md) for enforced
> rules and [CONTRIBUTING.md](../CONTRIBUTING.md) for paths and commands.

## Design

- **`marquise-components`** owns presentational UI and pure filter logic; it receives clients via props
- **`marquise-client`** owns client protocols, API types, and injected HTTP and mock implementations
- **Apps compose** library exports, configure clients, and pass them via props
- Each package builds, lints, typechecks, and tests on its own; client tests inject `fetch`

Full rules → [Atlas Clean Architecture](../atlas/50-processes/Clean%20Architecture.md) (modular web packages) and [AGENTS.md](../AGENTS.md).

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

- `/` is a poster-first discovery page with categories drawn from the current
  screening page's real movie genres. `/screenings` defaults to today in Montréal;
  date, movie title, cinema ID, exact language code (such as `VOF` or `VOSTF`),
  local time bounds, and page live in the URL and filter on the server.
  Legacy `/?date=…&cinema=…` links still open filtered daily listings. Old numeric
  hour bounds are supported; obsolete display controls and local genre filters
  are no longer controls in this interface.
- `/cinemas` searches names on the server and shows addresses, websites and links
  into cinema-filtered daily screenings. `/movies/<id>` resolves real movie
  metadata and pages that film's screenings for the selected date.
- Each active endpoint fetches **one requested page**: screenings and movie
  showtimes use 48 rows, cinemas use 100. Poster counts are unique films on that
  page; API pagination counts screenings. Films can recur on subsequent pages.
  Movie metadata enrichment requests at most 100 IDs from that page in one bulk
  call. Optional cinema website enrichment uses only the first 100 cinemas and
  never drains the directory. Missing optional cinema metadata preserves times
  and ticket links.
- The new interface uses the injected `DiscoveryClient` protocol. Retained
  `MovieGridClient.fetchForDate` and `MovieDetailClient.fetchShowtimes` APIs are
  compatibility collections: **HTTP returns only page one**, capped at 100 and
  48 screenings respectively. Their old local UI controls operate on that
  collection, not a complete date's catalogue. Use `DiscoveryClient` for totals,
  server filters and pagination. No endpoint is eagerly drained.
- Hover a poster for times; use its Showtimes button with keyboard or touch for
  the same preview, tickets and movie details. Previews render in a portal above
  horizontal rails. Posters lazy-load with reserved dimensions and title
  fallbacks; navigation, focus styles and reduced-motion support use native CSS.
- Local development defaults to explicitly labelled **demo** data. Production's
  Dockerfile defaults to `VITE_MARQUISE_DATA_SOURCE=api` and
  `VITE_MARQUISE_API_BASE_URL=https://api.marquise.mov`; set these at build time
  when building outside Docker. Turborepo forwards and includes both variables
  in its build cache key. No account or backend changes are required.
- On hosts with constrained worker/thread limits, run the full test suite as
  `RAYON_NUM_THREADS=2 pnpm test -- --maxWorkers=1`.

- `packages/components` ships a **prebuilt CSS bundle** (`dist/index.css`), so external
  consumers do not need their own Tailwind install. The workspace app resolves both the
  component code and stylesheet from source for fresh-checkout development and HMR.
- `marquise-interface` is the development and visual-test consumer for the shared component
  package; there is no second demo application to keep in sync.
- `marquise-interface` uses client-side routes including `/screenings`, `/cinemas`
  and `/movies/<id>`. Production
  static hosting must rewrite unknown document requests to `index.html` so direct movie
  links and refreshes load the Vite app.
