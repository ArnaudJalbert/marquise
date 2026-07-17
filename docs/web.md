# Web Front-End

Marquise's front-end lives in the [`web/`](https://github.com/ArnaudJalbert/marquise/tree/main/web) subtree of this repository as a **pnpm + [Turborepo](https://turbo.build/repo/docs) monorepo**. Keeping it in the same repo as the Python backend means the UI and the API contract evolve together under one CI pipeline.

The full, hands-on guide (every command, troubleshooting) is the [`web/README.md`](https://github.com/ArnaudJalbert/marquise/blob/main/web/README.md). This page is the high-level orientation.

> **No Python required.** The `web/` subtree is self-contained — you can develop the front-end with only Node.js and pnpm; you do not need `uv`, a database, or the backend running.

## Layout

```
web/
├── package.json          # Workspace root (private): Turborepo + shared scripts
├── pnpm-workspace.yaml   # Workspaces: apps/* and packages/*
├── turbo.json            # Task pipeline (build, dev, lint)
├── apps/
│   ├── marquise-admin/     # Admin web app — Vite + React 19 + TypeScript
│   └── marquise-interface/ # Consumer web app (poster wall) — Vite + React 19 + TypeScript
└── packages/
    ├── api-client/         # @marquise/api-client — typed fetch client for the Marquise API
    └── components/         # @marquise/components — shared components/utilities
```

- **`apps/*`** — runnable applications. `marquise-admin` (read-only internal admin) and `marquise-interface` (public consumer poster-wall prototype).
- **`packages/*`** — shared libraries. `@marquise/components` holds code used by more than one app — design tokens, the poster-wall component library, filter bar. `@marquise/api-client` is a dependency-free, hand-typed `fetch` wrapper around the `/v1` REST API. Both are consumed via the [`workspace:*`](https://pnpm.io/workspaces#workspace-protocol-workspace) protocol so apps always build against local source.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Node.js | ≥ 20 (developed on 26) | `node --version` |
| pnpm | 11.x (pinned in `web/package.json`) | Provisioned via [Corepack](https://nodejs.org/api/corepack.html) |

```bash
# Provision the pinned pnpm version reproducibly
corepack enable pnpm
# If `corepack` is missing (some Homebrew Node builds):
#   npm install -g corepack && corepack enable pnpm
```

## Quick start

```bash
cd web
pnpm install                            # install + link the whole workspace (run once)
pnpm --filter marquise-admin dev        # start the admin app (prints http://localhost:5173)
pnpm --filter marquise-interface dev    # start the poster-wall prototype app
```

## Common commands

Run from `web/`:

| Command | What it does |
|---|---|
| `pnpm install` | Install all workspaces, link internal packages. Re-run after any `package.json` change. |
| `pnpm --filter marquise-admin dev` | Admin app dev server with hot reload. |
| `pnpm --filter marquise-interface dev` | Poster-wall prototype app dev server with hot reload. |
| `pnpm build` | `turbo run build` — builds `@marquise/components`, then the apps (dependency-ordered, cached). |
| `pnpm lint` | `turbo run lint` — lints/type-checks every workspace. |
| `pnpm --filter <name> <script>` | Run one workspace's script (`<name>` = the package's `name`, e.g. `marquise-admin`, `@marquise/components`). |

Turborepo's [`turbo.json`](https://github.com/ArnaudJalbert/marquise/blob/main/web/turbo.json) declares `build` with `dependsOn: ["^build"]`, so `@marquise/components` is always built before the apps that import it, and unchanged outputs are served from cache.

## Build graph

```
packages/components (@marquise/components)   ──tsc──▶  dist/   (React is a peerDependency)
        │  consumed via "@marquise/components": "workspace:*"
        ▼
apps/marquise-admin, apps/marquise-interface              ──vite──▶ dist/    (static bundle)
```

## Status & scope

`marquise-admin` remains a toolchain skeleton with no product logic ([issue #64](https://github.com/ArnaudJalbert/marquise/issues/64)), beyond a minimal wiring smoke test for `@marquise/api-client`. `marquise-interface` is a new app that renders the poster-wall live prototype — four grid layouts plus a full interactive filter bar (search, cinema/language/genre, date picker, time-range slider) — built entirely on `@marquise/components` against a local mock-data fixture (16 movies). It has no live API connection yet; wiring `@marquise/api-client` into `marquise-interface` is a follow-up.

`@marquise/api-client` is a typed `fetch` client for the public, read-only `/v1` REST API at [`https://marquise-api.fly.dev`](https://marquise-api.fly.dev/docs) (movies, cinemas, screenings) — see [`packages/api-client/README.md`](https://github.com/ArnaudJalbert/marquise/blob/main/web/packages/api-client/README.md).

Explicitly out of scope so far (tracked as separate issues):

- Wiring `@marquise/api-client` into `marquise-interface`
- Routing (both apps are single-page)
- Web CI (the current GitHub Actions pipeline is Python-only)
