# Interface Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the interface bugs found during review and remove duplicated or unused frontend code while keeping `marquise-components` as a reusable package.

**Architecture:** Keep the existing `MovieGridClient` and `MovieDetailClient` boundaries for consumers, but have one HTTP implementation and one mock implementation satisfy both. Prefer native controls and the installed Radix primitives, keep layout policy inside the shared components, and retain the Vite app as the component library's development consumer.

**Tech Stack:** React 19, TypeScript 6, Vite 8, Vitest 4, pnpm workspaces, Radix UI, Fly.io.

## Global Constraints

- Keep `marquise-components` as an independent reusable package.
- Add no dependencies.
- Preserve the existing URL/history behavior and public grid/detail interfaces.
- Preserve nullable API links instead of inventing URLs.
- Do not commit without explicit user authorization.
- Run `pnpm test`, `pnpm typecheck`, `pnpm lint`, and `pnpm build` from `web/` before handoff.

---

### Task 1: Consolidate and correct data clients

**Files:**
- Modify: `web/packages/marquise-client/src/http-client.ts`
- Delete: `web/packages/marquise-client/src/http-movie-detail-client.ts`
- Modify: `web/packages/marquise-client/src/mock-client.ts`
- Modify: `web/packages/marquise-client/src/montreal-date.ts`
- Modify: `web/packages/marquise-client/src/cinema.ts`
- Modify: `web/packages/marquise-client/src/movie-grid-client.ts`
- Modify: `web/packages/marquise-client/src/index.ts`
- Modify tests under: `web/packages/marquise-client/src/*.test.ts`

**Interfaces:**
- Consumes: existing `MovieGridClient` and `MovieDetailClient` contracts.
- Produces: `HttpMarquiseClient` and `MockMarquiseClient`, each assignable to both contracts.

- [x] Add tests proving concurrent cinema lookups share one request, failed optional lookups can retry, horizon screenings are reused, nullable links remain null, mock grid/detail output is identical, and Montréal timestamps survive DST.
- [x] Run `pnpm --dir web --filter marquise-client test` and confirm the new assertions fail against the old implementations.
- [x] Implement one `HttpMarquiseClient` with an in-flight cinema promise and per-movie horizon screening cache. Use an optional `movie` parameter for `listDates(movie?: MovieCardData)` so one method satisfies both contracts.
- [x] Implement one `MockMarquiseClient` backed by a shared `itemsForDate(date)` function. Generate dates and timestamps with the existing Montréal helpers.
- [x] Remove the duplicate detail implementation and obsolete exports, then run client tests, typecheck, and lint.

### Task 2: Use native and installed interaction primitives

**Files:**
- Modify: `web/packages/components/src/components/movie/date-selector.tsx`
- Modify: `web/packages/components/src/components/movie/MovieDetailPage.tsx`
- Modify: `web/packages/components/src/components/movie/MovieCard.tsx`
- Modify: `web/packages/components/src/components/movie/CinemaShowtimes.tsx`
- Modify tests under: `web/packages/components/src/components/movie/*.test.tsx`

**Interfaces:**
- Consumes: nullable `Cinema.link` and `CinemaShowtime.ticketUrl`.
- Produces: the existing `DateSelector`, `MovieCard`, and `MovieDetailPage` APIs with accessible native/Radix behavior.

- [x] Add tests that missing cinema/ticket URLs render as text, not anchors, and that sparse dates remain selectable.
- [x] Replace the custom calendar implementation with previous/next buttons and a native `<select>` of available dates.
- [x] Replace the hand-built card portals, positioning, timers, Escape listener, and outside-click layer with the installed Radix `Popover` and `HoverCard` wrappers.
- [x] Render links only when a real URL exists; otherwise render the same label as plain text.
- [x] Run focused component tests, typecheck, and lint.

### Task 3: Correct layout, navigation, language, and time behavior

**Files:**
- Modify: `web/packages/components/src/components/movie/MovieCardGrid.tsx`
- Modify: `web/packages/components/src/components/movie/MovieCardGrid.test.tsx`
- Modify: `web/apps/marquise-interface/src/App.tsx`
- Modify: `web/apps/marquise-interface/src/index.css`
- Modify: `web/apps/marquise-interface/src/components/Header.tsx`
- Modify: `web/apps/marquise-interface/index.html`
- Modify relevant app tests.

**Interfaces:**
- Consumes: existing responsive measurements and URL state callbacks.
- Produces: row-aware auto-fit, scrollable narrow layouts, correct active navigation, and a current time refreshed once per minute.

- [x] Update auto-fit tests so `columns = min(widthColumns, max(2, ceil(items.length / availableRows)))` after row measurement.
- [x] Remove grid-level ArrowLeft/ArrowRight handling and its focus target; pagination buttons remain the keyboard interface.
- [x] Make the app's main region vertically scrollable on narrow screens while retaining the bounded desktop grid.
- [x] Fix `aria-current`, set the document language to `en-CA`, and replace module-level client instances with a lazy component-owned shared client.
- [x] Refresh `currentTime` every minute and run focused app/component tests.

### Task 4: Remove unused and duplicated package surface

**Files:**
- Modify: `web/packages/components/src/index.ts`
- Modify: `web/packages/components/src/components/ui/card.tsx`
- Delete: `web/packages/components/src/components/ui/badge.tsx`
- Delete: `web/packages/components/src/components/ui/separator.tsx`
- Delete: `web/packages/components/src/components/movie/cinema.ts`
- Delete: `web/packages/components/src/components/movie/movie.ts`
- Delete: `web/packages/components/src/components/movie/movie-grid-client.ts`
- Delete: `web/packages/components/src/components/movie/movie-detail-client.ts`
- Delete: `web/packages/components/demo/main.tsx`
- Delete: `web/packages/components/index.html`
- Modify: `web/packages/components/vite.config.ts`
- Modify: `web/packages/components/package.json`
- Modify imports throughout `web/packages/components/src`.

**Interfaces:**
- Consumes: types directly from `marquise-client`.
- Produces: the same movie component API without one-line proxy modules or unused UI exports.

- [x] Point internal type imports and public type exports directly at `marquise-client`.
- [x] Keep only the used `Card` and `CardContent` functions and remove unused Badge/Separator files and dependency.
- [x] Delete the duplicate demo and its slow-poster Vite server plugin; use `marquise-interface` as the live development consumer.
- [x] Run component tests, typecheck, lint, and build.

### Task 5: Make local and deployed configuration reproducible

**Files:**
- Modify: `web/apps/marquise-interface/vite.config.ts`
- Modify: `apps/marquise-api/fly.toml`
- Modify: `web/README.md`
- Modify: `docs/superpowers/plans/2026-08-08-auto-fit-grid-rows.md`

**Interfaces:**
- Produces: a fresh-checkout dev command that resolves component CSS from source and a Fly API config that declares the deployed interface origin.

- [x] Alias `marquise-components/index.css` to the component source stylesheet in the interface Vite config.
- [x] Declare `MARQUISE_API_CORS_ORIGINS = "https://marquise-interface.fly.dev"` in the API Fly environment.
- [x] Update the web README to describe the single app dev server and source-based workspace HMR.
- [x] Mark the existing auto-fit plan complete after its behavior and tests are implemented.
- [x] Run the full web quality gates and `git diff --check`; inspect `git status` to ensure only intended source/docs changes remain.

## Self-Review

- Spec coverage: every important and smaller review finding is covered; package collapse is explicitly excluded.
- Placeholder scan: no deferred implementation placeholders are present.
- Type consistency: both concrete clients implement the unchanged grid/detail contracts; nullable link types flow through client and component layers.
