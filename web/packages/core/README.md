# @marquise/core

Shared React components and utilities for the Marquise web apps. This is an **internal, unpublished** workspace package — consumed by [`marquise-admin`](../../apps/marquise-admin) (and the future consumer app) via the `workspace:*` protocol, never installed from a registry.

## What lives here

Code shared across more than one app: UI components, hooks, formatting helpers, and (later) the generated API client / types. If a piece of code is used by only one app, keep it in that app; promote it here when a second app needs it.

Currently it exports a single smoke-test component, `CoreHello`, that proves the workspace wiring end-to-end.

## Consuming it

Add the dependency (already done for `marquise-admin`):

```jsonc
// apps/<app>/package.json
"dependencies": {
  "@marquise/core": "workspace:*"
}
```

Then import by scope — the workspace resolves it to this package's built output:

```tsx
import { CoreHello } from '@marquise/core'
```

## Adding an export

1. Add your component/util under `src/`.
2. Re-export it from [`src/index.tsx`](src/index.tsx) (the package entry point).
3. `pnpm --filter @marquise/core build` to emit `dist/`.

React is a **peer dependency** — the consuming app provides the single React instance, so there is never a duplicate React runtime.

## Build

```bash
# From web/ — build just this package
pnpm --filter @marquise/core build   # tsc -> dist/ (JS + .d.ts)

# Type-check without emitting
pnpm --filter @marquise/core lint
```

`turbo run build` at the workspace root builds this package **before** any app that depends on it (via `dependsOn: ["^build"]` in [`web/turbo.json`](../../turbo.json)).

## Package details

| | |
|---|---|
| Entry | `src/index.tsx` → built to `dist/index.js` + `dist/index.d.ts` |
| Module type | ESM (`"type": "module"`) |
| Build tool | `tsc` (config in [`tsconfig.json`](tsconfig.json)) |
| Peer deps | `react`, `react-dom` |
