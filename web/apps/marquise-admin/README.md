# marquise-admin

The Marquise **admin web app** (read-only) — a [Vite](https://vite.dev/) + [React](https://react.dev/) + TypeScript single-page app. It lives in the `web/` [monorepo](../../README.md) and shares code with [`marquise-interface`](../marquise-interface) through the [`@marquise/components`](../../packages/components) package, and talks to the backend via [`@marquise/api-client`](../../packages/api-client).

> This is still mostly a bare toolchain skeleton (the default Vite starter page), plus a minimal wiring smoke test that fetches the tracked cinema count via `@marquise/api-client`. Real admin screens — routing, UI kit — arrive in follow-up issues.

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
| Shared code | [`@marquise/components`](../../packages/components) via `workspace:*` |
| API client | [`@marquise/api-client`](../../packages/api-client) via `workspace:*` |

## Structure

```
apps/marquise-admin/
├── index.html          # Vite entry HTML
├── src/
│   ├── main.tsx        # React root
│   ├── App.tsx         # App shell
│   └── *.css, assets/
├── vite.config.ts
├── tsconfig*.json      # app / node project references
└── .oxlintrc.json      # lint rules
```

### Using shared components

Import from the shared package by its scope; the workspace resolves it to local source:

```tsx
import { PosterWall } from '@marquise/components'
```

To add a new shared component, put it in [`packages/components`](../../packages/components) and export it from its entry point — do not duplicate shared UI inside this app.
