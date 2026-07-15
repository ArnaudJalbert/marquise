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
│   └── marquise-admin/   # Admin web app — Vite + React 19 + TypeScript
└── packages/
    └── core/             # @marquise/core — shared components/utilities
```

- **`apps/*`** — runnable applications. Today: the read-only admin app. Later: the public consumer app, as another sibling.
- **`packages/*`** — shared libraries. `@marquise/core` holds code used by more than one app, consumed via the [`workspace:*`](https://pnpm.io/workspaces#workspace-protocol-workspace) protocol so apps always build against local source.

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
pnpm install                        # install + link the whole workspace (run once)
pnpm --filter marquise-admin dev    # start the admin app (prints http://localhost:5173)
```

## Common commands

Run from `web/`:

| Command | What it does |
|---|---|
| `pnpm install` | Install all workspaces, link internal packages. Re-run after any `package.json` change. |
| `pnpm --filter marquise-admin dev` | Admin app dev server with hot reload. |
| `pnpm build` | `turbo run build` — builds `@marquise/core`, then the apps (dependency-ordered, cached). |
| `pnpm lint` | `turbo run lint` — lints/type-checks every workspace. |
| `pnpm --filter <name> <script>` | Run one workspace's script (`<name>` = the package's `name`, e.g. `marquise-admin`, `@marquise/core`). |

Turborepo's [`turbo.json`](https://github.com/ArnaudJalbert/marquise/blob/main/web/turbo.json) declares `build` with `dependsOn: ["^build"]`, so `@marquise/core` is always built before the apps that import it, and unchanged outputs are served from cache.

## Build graph

```
packages/core (@marquise/core)   ──tsc──▶  dist/   (React is a peerDependency)
        │  consumed via "@marquise/core": "workspace:*"
        ▼
apps/marquise-admin              ──vite──▶ dist/    (static bundle)
```

## Status & scope

The web workspace is currently a **toolchain skeleton** ([issue #64](https://github.com/ArnaudJalbert/marquise/issues/64)). The admin app renders a `CoreHello` component from `@marquise/core` to prove the wiring; there is no product logic yet.

Explicitly out of scope for the scaffold (tracked as separate issues):

- API client / data fetching against [`https://marquise-api.fly.dev`](https://marquise-api.fly.dev/docs)
- Routing and a UI component kit
- Web CI (the current GitHub Actions pipeline is Python-only)
