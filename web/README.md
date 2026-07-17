# Marquise Web

The front-end monorepo for Marquise. This is a [pnpm workspace](https://pnpm.io/workspaces) orchestrated by [Turborepo](https://turbo.build/repo/docs), living alongside the Python backend in the same repository so the UI and the API contract evolve under one CI pipeline.

> **You do not need Python, `uv`, or a database to work on the web apps.** This subtree is self-contained. The only prerequisites are Node.js and pnpm (see below).

## Layout

```
web/
├── package.json          # Workspace root (private): Turborepo + shared scripts
├── pnpm-workspace.yaml   # Declares the workspaces: apps/* and packages/*
├── turbo.json            # Task pipeline (build, dev, lint)
├── pnpm-lock.yaml        # Single lockfile for the whole workspace
├── apps/
│   ├── marquise-admin/     # Admin web app — Vite + React + TypeScript
│   └── marquise-interface/ # Consumer web app (poster wall) — Vite + React + TypeScript
└── packages/
    ├── api-client/         # @marquise/api-client — typed fetch client for the Marquise API
    └── components/         # @marquise/components — shared components/utilities
```

The convention is **Turborepo standard**: runnable applications live under `apps/*`, shared libraries under `packages/*`. Internal packages use the `@marquise/*` npm scope and are consumed via the [`workspace:*`](https://pnpm.io/workspaces#workspace-protocol-workspace) protocol (see [`apps/marquise-admin/package.json`](apps/marquise-admin/package.json)), so an app always builds against the local source of `@marquise/components`, never a published version.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| [Node.js](https://nodejs.org/) | ≥ 20 (developed on 26) | `node --version` |
| [pnpm](https://pnpm.io/) | 11.x (pinned) | Provisioned via Corepack — see below |

The exact pnpm version is pinned in the root [`package.json`](package.json) `packageManager` field. The reproducible way to get it is [Corepack](https://nodejs.org/api/corepack.html), which ships the right pnpm version automatically:

```bash
# If your Node build includes Corepack (most do):
corepack enable pnpm

# If `corepack` is not found (e.g. some Homebrew Node builds):
npm install -g corepack
corepack enable pnpm

# Verify — should match the packageManager field in package.json
pnpm --version
```

> Prefer Corepack over a global `npm install -g pnpm`: it guarantees everyone uses the pinned version, avoiding "works on my machine" lockfile drift.

## Getting started

All commands below are run **from the `web/` directory** unless noted.

```bash
cd web

# Install every workspace's dependencies and link internal packages.
# Run this once after cloning, and again whenever any package.json changes.
pnpm install
```

`pnpm install` resolves the whole workspace at once and symlinks `@marquise/components` into the apps that depend on it — there is no separate "build the library first" step for local development.

## Everyday commands

Two equivalent ways to run tasks: through **Turborepo** (runs across all workspaces, respects dependencies, caches results) or through **pnpm `--filter`** (targets one workspace).

### Run the admin app in dev mode (most common)

```bash
# Start the Vite dev server with hot-module reload
pnpm --filter marquise-admin dev
```

Vite prints the local URL (default <http://localhost:5173>). Leave it running; edits to `apps/marquise-admin` **or** to `packages/components` hot-reload live.

### Workspace-wide tasks (via Turborepo)

```bash
pnpm build   # turbo run build — builds @marquise/components, then the apps (respects ^build order)
pnpm lint    # turbo run lint  — lints/type-checks every workspace
pnpm dev     # turbo run dev   — runs the dev task of every app in parallel
```

These delegate to `turbo run <task>` (see the root [`package.json`](package.json) scripts). Turborepo reads [`turbo.json`](turbo.json): the `build` task declares `"dependsOn": ["^build"]`, so `@marquise/components` is always built before any app that imports it, and outputs (`dist/**`) are cached — a second `pnpm build` with no changes is near-instant.

### Targeting a single workspace (via pnpm)

```bash
pnpm --filter marquise-admin <script>   # e.g. dev, build, lint, preview
pnpm --filter @marquise/components <script>   # e.g. build, lint

# Preview a production build of the admin app locally
pnpm --filter marquise-admin build
pnpm --filter marquise-admin preview
```

> `--filter` takes the workspace's **package name** (the `name` field in its `package.json`), i.e. `marquise-admin` and `@marquise/components` — not the folder path.

### Managing dependencies

```bash
# Add a runtime dependency to the admin app
pnpm --filter marquise-admin add <pkg>

# Add a dev dependency to the core package
pnpm --filter @marquise/components add -D <pkg>

# Add a tool to the workspace root (e.g. turbo itself)
pnpm add -w -D <pkg>

# Make the admin app depend on the shared package
pnpm --filter marquise-admin add @marquise/components@workspace:*
```

## The apps and packages

| Workspace | Path | Description |
|---|---|---|
| `marquise-admin` | [`apps/marquise-admin`](apps/marquise-admin) | Admin web app (read-only). Vite + React 19 + TypeScript. See its [README](apps/marquise-admin/README.md). |
| `marquise-interface` | [`apps/marquise-interface`](apps/marquise-interface) | Consumer web app — the poster-wall live prototype. Vite + React 19 + TypeScript. See its [README](apps/marquise-interface/README.md). |
| `@marquise/components` | [`packages/components`](packages/components) | Shared React components and utilities used by both apps. See its [README](packages/components/README.md). |
| `@marquise/api-client` | [`packages/api-client`](packages/api-client) | Typed, dependency-free `fetch` client for the Marquise API. See its [README](packages/api-client/README.md). |

## How it fits together

```
packages/components (@marquise/components)      packages/api-client (@marquise/api-client)
  built by `tsc` → dist/                           built by `tsc` → dist/
  (React is a peerDependency, no duplicate React)   (no runtime deps)
  "@marquise/components": "workspace:*"             "@marquise/api-client": "workspace:*"
        │                                                  │
        └──────────────────────┬───────────────────────────┘
                                ▼
        apps/marquise-admin, apps/marquise-interface  ──vite──▶  dist/  (static bundle)
```

`turbo run build` walks this graph bottom-up: `@marquise/components` and `@marquise/api-client` first (independent of each other), then the apps.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `corepack: command not found` | `npm install -g corepack`, then `corepack enable pnpm`. |
| pnpm version differs from `packageManager` | Run `corepack enable pnpm` again; don't `npm i -g pnpm`. |
| App can't resolve `@marquise/components` | Run `pnpm install` from `web/` so the workspace symlink is (re)created. |
| Port 5173 already in use | Vite auto-increments; read the actual URL it prints. Or `pnpm --filter marquise-admin dev -- --port 5174`. |
| Stale/odd build output | `pnpm --filter <name> build` again, or clear caches: `rm -rf .turbo apps/*/dist packages/*/dist`. |

## What is intentionally *not* here yet

Per the scaffold scope ([issue #64](https://github.com/ArnaudJalbert/marquise/issues/64)), the following are separate follow-up issues and are **not** wired up:

- Routing and a UI component kit
- Web CI (the existing GitHub Actions pipeline is Python-only)

See the repository's [web documentation](../docs/web.md) for the higher-level overview.
