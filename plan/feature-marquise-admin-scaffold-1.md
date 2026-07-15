---
goal: Scaffold a Turborepo (pnpm) web monorepo with the Vite + React + TS admin app and a shared core package
version: 2.0
date_created: 2026-07-15
last_updated: 2026-07-15
owner: Arnaud Jalbert
status: 'Planned'
tags: [feature, frontend, scaffold, monorepo, turborepo]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Bootstrap a `web/` Turborepo monorepo inside the existing Python repo. `web/` is a pnpm + Turborepo workspace that manages multiple web applications and shared packages under one CI pipeline, keeping the UI and API contract in sync. This plan delivers: (1) the workspace tooling (Turborepo, pnpm workspaces, root config), (2) the bare Vite + React + TS admin app at `web/apps/marquise-admin`, and (3) a shared `@marquise/core` package at `web/packages/core` that the admin app (and the future consumer app) import shared components from. No product/app logic, routing, API client, or UI kit is added. This extends and supersedes the single-app scope of [issue #64](https://github.com/ArnaudJalbert/marquise/issues/64).

## 1. Requirements & Constraints

- **REQ-001**: `web/` MUST be a Turborepo monorepo driven by pnpm workspaces.
- **REQ-002**: The admin app MUST be a Vite `react-ts` project located at `web/apps/marquise-admin`.
- **REQ-003**: A shared package `@marquise/core` MUST exist at `web/packages/core`, buildable and importable as a workspace dependency.
- **REQ-004**: The admin app MUST declare `@marquise/core` as a `workspace:*` dependency and successfully import at least one export from it (a smoke-test component) to prove the wiring.
- **REQ-005**: `pnpm --filter marquise-admin dev` MUST serve the Vite starter page; `pnpm --filter marquise-admin build` MUST produce a `dist/` bundle.
- **REQ-006**: `pnpm turbo run build` from `web/` MUST build both `core` and `marquise-admin`, resolving `core` before the app via task dependencies.
- **REQ-007**: Root `.gitignore` MUST exclude web `node_modules`, build outputs (`dist`, `.turbo`), and `.env` for all workspace paths.
- **REQ-008**: No product logic, routing, data fetching, API client, or UI kit is added beyond the single smoke-test component in `core`.
- **CON-001**: The Python project (`src/`, `pyproject.toml`, `uv`) MUST remain untouched and functional; the web workspace is fully independent of the Python toolchain.
- **CON-002**: No changes to `pyproject.toml` or `uv.lock`.
- **CON-003**: No `node_modules`, `dist`, or `.turbo` directory may be committed.
- **CON-004**: Package manager is pnpm; npm/yarn lockfiles MUST NOT be committed under `web/`.
- **GUD-001**: Node v26.5.0 confirmed available; pnpm installed via Corepack (`corepack enable pnpm`) to pin a repo-wide version.
- **GUD-002**: Follow project commit conventions: branch `feat/`, commit `type(scope): description`, add a `CHANGELOG.md` entry.
- **PAT-001**: Turborepo standard layout — apps under `web/apps/*`, shared packages under `web/packages/*`.
- **PAT-002**: Internal packages use the `@marquise/*` npm scope and are consumed via the `workspace:*` protocol.
- **PAT-003**: The workspace root `package.json` is `private: true` and holds Turborepo, pnpm workspace config, and root scripts only — no app dependencies.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Establish the pnpm + Turborepo workspace root at `web/`.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create feature branch `feat/scaffold-web-monorepo` off `main` (or continue on current branch if instructed). | | |
| TASK-002 | Run `corepack enable pnpm` and pin a version (e.g. `corepack use pnpm@latest`) so the pnpm version is reproducible. | | |
| TASK-003 | Create `web/` with a root `package.json`: `"private": true`, `"name": "marquise-web"`, `packageManager` field (matching TASK-002), and scripts `dev`/`build`/`lint` that delegate to `turbo run <task>`. | | |
| TASK-004 | Create `web/pnpm-workspace.yaml` declaring `packages: ["apps/*", "packages/*"]`. | | |
| TASK-005 | Add Turborepo as a root dev dependency: `pnpm -w add -D turbo`. Create `web/turbo.json` defining a `build` pipeline task with `"dependsOn": ["^build"]` and `"outputs": ["dist/**"]`, plus `dev` (`"cache": false, "persistent": true`) and `lint` tasks. | | |

### Implementation Phase 2

- GOAL-002: Create the shared `@marquise/core` package.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Create `web/packages/core` with `package.json`: `"name": "@marquise/core"`, `"private": true`, `"version": "0.0.0"`, `main`/`types`/`exports` pointing at a built `dist/` (or `src/index.ts` for a source-only internal package), and a `build` script (`tsc` or `tsup`). | | |
| TASK-007 | Add a `tsconfig.json` to `web/packages/core` and a minimal `src/index.ts` exporting one smoke-test React component (e.g. `export function CoreHello(): JSX.Element`). Add React + TypeScript as needed (`react` as a peer/dev dep). | | |
| TASK-008 | Run `pnpm --filter @marquise/core build` and confirm it emits type-correct output without errors. | | |

### Implementation Phase 3

- GOAL-003: Scaffold the admin app and wire it to `@marquise/core`.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-009 | Scaffold the app: `pnpm create vite@latest web/apps/marquise-admin --template react-ts` (select React + TypeScript if prompted). | | |
| TASK-010 | In `web/apps/marquise-admin/package.json`, set `"name": "marquise-admin"` and add `"@marquise/core": "workspace:*"` to dependencies. | | |
| TASK-011 | Run `pnpm install` at `web/` root to link the workspace (creates `web/pnpm-lock.yaml` and symlinks `@marquise/core`). | | |
| TASK-012 | Edit `web/apps/marquise-admin/src/App.tsx` to import and render `CoreHello` from `@marquise/core`, proving the shared package resolves. | | |
| TASK-013 | Verify `pnpm --filter marquise-admin dev` serves the page (read the actual URL from stdout) and the `CoreHello` component renders; then stop the server. | | |

### Implementation Phase 4

- GOAL-004: Validate the whole workspace and wire repo hygiene.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-014 | From `web/` run `pnpm turbo run build` and confirm Turborepo builds `@marquise/core` before `marquise-admin` (via `^build`) with no errors; then `pnpm turbo run lint`. | | |
| TASK-015 | Edit root `.gitignore`: add a `# Web (pnpm + Turborepo monorepo)` section with `web/**/node_modules`, `web/**/dist`, `web/**/.turbo`, and `web/**/.env`. | | |
| TASK-016 | Run `git status --porcelain` and `git check-ignore` to confirm no `node_modules`, `dist`, or `.turbo` paths are tracked; tracked additions are source, configs, and `web/pnpm-lock.yaml`. | | |
| TASK-017 | Add a `CHANGELOG.md` entry under `Unreleased`/`Added` noting the `web/` Turborepo monorepo, `@marquise/core`, and `marquise-admin` scaffold (issue #64). Do NOT bump `pyproject.toml` version. | | |
| TASK-018 | Confirm the Python side is unaffected: `uv run pytest tests/unit_tests/ -q`. Then commit `feat(web): scaffold pnpm + Turborepo monorepo with marquise-admin and @marquise/core`, referencing `Closes #64` in the PR body. | | |

## 3. Alternatives

- **ALT-001**: Single Vite app at `web/marquise-admin` with no monorepo tooling (original issue #64 scope). Rejected: the user requires Turborepo to manage multiple apps and a shared `core` package.
- **ALT-002**: Flat layout (`web/marquise-admin`, `web/core`) instead of `apps/*` + `packages/*`. Rejected: `apps/`/`packages/` is the idiomatic Turborepo convention and scales cleanly when the consumer app is added.
- **ALT-003**: npm or yarn workspaces instead of pnpm. Rejected: pnpm is Turborepo's recommended manager — strict package boundaries (prevents phantom deps between `core` and apps), faster installs, less disk.
- **ALT-004**: Nx instead of Turborepo. Rejected: heavier; Turborepo is sufficient and lower-config for this repo's needs.
- **ALT-005**: Publish `@marquise/core` to a registry. Rejected: it is an internal-only workspace package consumed via `workspace:*`.

## 4. Dependencies

- **DEP-001**: Node.js v26.5.0 (confirmed installed).
- **DEP-002**: Corepack (bundled with Node) to provision a pinned pnpm version.
- **DEP-003**: pnpm (installed/pinned via Corepack).
- **DEP-004**: `turbo` (root dev dependency).
- **DEP-005**: Network access to the npm registry for `pnpm create vite`, `turbo`, and package installs.
- **DEP-006**: Vite `react-ts` template; `typescript`, `react`, `react-dom`; a `core` build tool (`tsc` or `tsup`).

## 5. Files

- **FILE-001**: `web/package.json` — private workspace root; Turborepo dev dep, `packageManager` field, root `dev`/`build`/`lint` scripts.
- **FILE-002**: `web/pnpm-workspace.yaml` — declares `apps/*` and `packages/*` workspaces.
- **FILE-003**: `web/turbo.json` — Turborepo pipeline (`build` with `^build` + `dist/**` outputs, `dev` persistent/uncached, `lint`).
- **FILE-004**: `web/pnpm-lock.yaml` — generated lockfile (committed).
- **FILE-005**: `web/packages/core/` — `@marquise/core` package: `package.json`, `tsconfig.json`, `src/index.ts` with the `CoreHello` smoke-test export.
- **FILE-006**: `web/apps/marquise-admin/` — Vite React-TS app: `src/`, `index.html`, `package.json` (depends on `@marquise/core`), `vite.config.ts`, `tsconfig*.json`, `eslint.config.js`, `public/`.
- **FILE-007**: `.gitignore` (repo root) — ignore web `node_modules`, `dist`, `.turbo`, `.env`.
- **FILE-008**: `CHANGELOG.md` (repo root) — entry documenting the monorepo scaffold.

## 6. Testing

- **TEST-001**: `pnpm --filter @marquise/core build` exits 0 and emits `core` build output/types.
- **TEST-002**: `pnpm --filter marquise-admin dev` serves the starter page and renders the imported `CoreHello` component (manual/observed).
- **TEST-003**: `pnpm --filter marquise-admin build` exits 0 and creates `web/apps/marquise-admin/dist/index.html`.
- **TEST-004**: `pnpm turbo run build` from `web/` builds `core` before `marquise-admin` with no errors and reports Turborepo caching.
- **TEST-005**: `pnpm turbo run lint` exits 0 across the workspace.
- **TEST-006**: `git check-ignore web/apps/marquise-admin/node_modules web/**/.turbo` confirms ignored paths; `git status` shows no build artifacts tracked.
- **TEST-007**: `uv run pytest tests/unit_tests/ -q` still passes (Python unaffected).

## 7. Risks & Assumptions

- **RISK-001**: `pnpm create vite@latest` may prompt interactively despite `--template react-ts`; mitigate by answering React + TypeScript or pinning the create-vite version.
- **RISK-002**: `@marquise/core` consumption model (source-only vs. built `dist/`) affects Vite/TS config; decide in TASK-006 — a built `dist` with `exports` is the most portable. If source-only, ensure the admin app's `tsconfig`/Vite can resolve the workspace TS source.
- **RISK-003**: React must not be duplicated between `core` and the app; declare `react`/`react-dom` as peer deps in `core` to avoid two React copies at runtime.
- **RISK-004**: The Vite default dev port (5173) may be occupied; Vite auto-increments — read the served URL from stdout.
- **RISK-005**: Existing CI (`.github/workflows/ci.yml`) is Python-only and will not build/test `web/`; adding web CI (Turborepo tasks) is a follow-up issue and out of scope here.
- **ASSUMPTION-001**: `web/` does not yet exist and is created by this plan (confirmed: no `web` directory present).
- **ASSUMPTION-002**: The "actual app" (consumer front end) will later be added under `web/apps/*` and will also depend on `@marquise/core`; the layout is designed for that but the app itself is out of scope.
- **ASSUMPTION-003**: Corepack is permitted in the dev environment to pin pnpm.

## 8. Related Specifications / Further Reading

- [Issue #64 — Scaffold Vite + React + TS project in web/](https://github.com/ArnaudJalbert/marquise/issues/64)
- [Turborepo documentation](https://turbo.build/repo/docs)
- [Turborepo — Structuring a repository (apps/ and packages/)](https://turbo.build/repo/docs/crafting-your-repository/structuring-a-repository)
- [pnpm Workspaces](https://pnpm.io/workspaces)
- [Vite — Getting Started](https://vitejs.dev/guide/)
- Repo convention: `web/` is a Turborepo monorepo; apps live under `web/apps/*`, shared code under `web/packages/*` (`@marquise/core`).
