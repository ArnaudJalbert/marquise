# marquise-admin

The Marquise **admin web app** (read-only) — a [Vite](https://vite.dev/) + [React](https://react.dev/) + TypeScript single-page app. It lives in the `web/` [monorepo](../../README.md) and shares code with the future consumer app through the [`@marquise/core`](../../packages/core) package.

> This is currently a bare toolchain skeleton (the default Vite starter page plus a `CoreHello` smoke-test component imported from `@marquise/core`). App logic — API client, routing, UI kit — arrives in follow-up issues.

## Prerequisites & install

This app is part of the pnpm + Turborepo workspace. Set up Node + pnpm and install dependencies **once from the workspace root**, as described in [`web/README.md`](../../README.md#getting-started):

```bash
cd web
pnpm install
```

Do not run `npm install` inside this folder — dependencies are managed by the workspace lockfile at `web/pnpm-lock.yaml`.

## Run it

From anywhere in the repo:

```bash
# Dev server with hot-module reload (prints its URL, default http://localhost:5173)
pnpm --filter marquise-admin dev

# Type-check + production build → dist/
pnpm --filter marquise-admin build

# Serve the production build locally
pnpm --filter marquise-admin preview

# Lint (oxlint)
pnpm --filter marquise-admin lint
```

Or, from `web/`, `pnpm dev` / `pnpm build` / `pnpm lint` run the task across the whole workspace via Turborepo.

## Stack

| Concern | Choice |
|---|---|
| Bundler / dev server | Vite 8 (`@vitejs/plugin-react`) |
| UI library | React 19 |
| Language | TypeScript |
| Linter | [oxlint](https://oxc.rs) (config in [`.oxlintrc.json`](.oxlintrc.json)) |
| Shared code | [`@marquise/core`](../../packages/core) via `workspace:*` |

## Structure

```
apps/marquise-admin/
├── index.html          # Vite entry HTML
├── src/
│   ├── main.tsx        # React root
│   ├── App.tsx         # Renders <CoreHello /> from @marquise/core (wiring smoke test)
│   └── *.css, assets/
├── vite.config.ts
├── tsconfig*.json      # app / node project references
└── .oxlintrc.json      # lint rules
```

### Using shared components

Import from the shared package by its scope; the workspace resolves it to local source:

```tsx
import { CoreHello } from '@marquise/core'
```

To add a new shared component, put it in [`packages/core`](../../packages/core) and export it from its entry point — do not duplicate shared UI inside this app.
