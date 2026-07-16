# marquise-interface

The **Poster Wall live prototype** — a public consumer-site preview built entirely on [`@marquise/components`](../../packages/components), using local mock data (no live API yet). It's the seed of the future public Marquise website: a [Vite](https://vite.dev/) + [React](https://react.dev/) + TypeScript single-page app, wired to a full interactive filter bar (search, cinema/language/genre, date picker, time-range slider) and all four approved poster-wall grid layouts.

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
pnpm --filter marquise-interface dev

# Type-check + production build → dist/
pnpm --filter marquise-interface build

# Serve the production build locally
pnpm --filter marquise-interface preview

# Lint (oxlint)
pnpm --filter marquise-interface lint
```

## Stack

| Concern | Choice |
|---|---|
| Bundler / dev server | Vite 8 (`@vitejs/plugin-react`) |
| UI library | React 19 |
| Language | TypeScript |
| Linter | [oxlint](https://oxc.rs) (config in [`.oxlintrc.json`](.oxlintrc.json)) |
| Shared code | [`@marquise/components`](../../packages/components) via `workspace:*` |
| Data | Local mock fixture (`src/data/movies.ts`) — no live API |

## Structure

```
apps/marquise-interface/
├── index.html               # Vite entry HTML, Google Fonts <link> tags
├── src/
│   ├── main.tsx              # React root, imports @marquise/components/styles.css
│   ├── App.tsx                # Renders <PosterWallPage />
│   ├── PosterWallPage.tsx     # Composition root: FilterBar + PosterWall, useState/useMemo filtering
│   ├── filterMovies.ts        # Pure AND-filter logic over the mock fixture
│   └── data/movies.ts         # 17-movie mock fixture
├── vite.config.ts
├── tsconfig*.json            # app / node project references
└── .oxlintrc.json            # lint rules
```

## Mock data & posters

`src/data/movies.ts` reproduces the mock movie set from the Poster Wall design spec. Most entries use **real theatrical poster art hotlinked from Wikipedia/Wikimedia Commons** (`upload.wikimedia.org`) rather than files checked into this repo — avoids licensing/redistribution concerns and repo bloat for a prototype fixture, while still showing the layouts with real photography.

One entry ("Rex: A Dinosaur's Story", a mock title from the design spec's own placeholder data that doesn't correspond to a real released film) intentionally has no resolvable poster URL — `PosterImage` (from `@marquise/components`) catches the load failure and renders the design system's documented neutral placeholder (`--n-100` background + glyph) instead of a fake illustrated poster, so both code paths stay exercised.

To swap in different art: update the `POSTERS` map at the top of `src/data/movies.ts` with any URL (hotlinked or a local `public/` asset) — no other code changes needed.

## Using shared components

```tsx
import { FilterBar, PosterWall } from '@marquise/components'
```

To add a new shared component, put it in [`packages/components`](../../packages/components) and export it from its entry point — do not duplicate shared UI inside this app.
