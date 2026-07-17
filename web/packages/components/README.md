# @marquise/components

Shared React components and utilities for the Marquise web apps. This is an **internal, unpublished** workspace package — consumed by [`marquise-admin`](../../apps/marquise-admin) and [`marquise-interface`](../../apps/marquise-interface) via the `workspace:*` protocol, never installed from a registry.

## What lives here

Code shared across more than one app: UI components, hooks, formatting helpers, and (later) the generated API client / types. If a piece of code is used by only one app, keep it in that app; promote it here when a second app needs it.

This package now holds the Marquise design system's poster-wall UI: design tokens (colors, typography, spacing/radii/shadow/motion), the `Poster*` card/grid family for the four approved poster-wall layouts, the full filter-bar component set (search, multi-select popovers, view switcher, date picker, dual-range time slider), and shared utilities (`dateKey`, `genrePalette`, `filterMovies`). See [`src/index.tsx`](src/index.tsx) for the full export surface.

## Consuming it

Add the dependency (already done for `marquise-admin` and `marquise-interface`):

```jsonc
// apps/<app>/package.json
"dependencies": {
  "@marquise/components": "workspace:*"
}
```

Then import by scope — the workspace resolves it to this package's built output:

```tsx
import { PosterWall, FilterBar } from '@marquise/components'
```

## Styles

Import the design-token stylesheet once at the consuming app's entry point, before any app-level CSS:

```tsx
// src/main.tsx
import '@marquise/components/styles.css'
import './index.css'
```

The three Marquise typefaces (Space Grotesk, Newsreader, IBM Plex Mono) are **not** bundled by this stylesheet — load them via `<link>` tags in the consuming app's `index.html` (see [`marquise-interface/index.html`](../../apps/marquise-interface/index.html) for the exact tags). Self-hosting the fonts instead of using Google Fonts is a future optimization (better privacy/performance, no third-party request), not done yet.

## Adding an export

1. Add your component/util under `src/`.
2. Re-export it from [`src/index.tsx`](src/index.tsx) (the package entry point).
3. `pnpm --filter @marquise/components build` to emit `dist/`.

React is a **peer dependency** — the consuming app provides the single React instance, so there is never a duplicate React runtime. `lucide-react` is a regular dependency, used internally for icons.

## Tests

```bash
# From web/ — run once
pnpm --filter @marquise/components test

# Watch mode
pnpm --filter @marquise/components test:watch
```

Uses `vitest` with `jsdom` and `@testing-library/react`. Test files live alongside their source (`*.test.ts` / `*.test.tsx`).

## Build

```bash
# From web/ — build just this package
pnpm --filter @marquise/components build   # tsc -> dist/ (JS + .d.ts), then mirrors every *.css file into dist/

# Type-check without emitting
pnpm --filter @marquise/components lint
```

`turbo run build` at the workspace root builds this package **before** any app that depends on it (via `dependsOn: ["^build"]` in [`web/turbo.json`](../../turbo.json)).

## Package details

| | |
|---|---|
| Entry | `src/index.tsx` → built to `dist/index.js` + `dist/index.d.ts` |
| Styles | `src/styles/index.css` → copied to `dist/styles/index.css`, exported as `@marquise/components/styles.css` |
| Module type | ESM (`"type": "module"`) |
| Build tool | `tsc` (config in [`tsconfig.json`](tsconfig.json)), styles mirrored via [`scripts/copy-css.mjs`](scripts/copy-css.mjs) |
| Peer deps | `react`, `react-dom` |
| Deps | `lucide-react` (icons) |
