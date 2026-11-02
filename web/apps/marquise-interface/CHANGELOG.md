# Changelog

## 2026-11-01

- Show the Marquise favicon (yellow strip in dark browser themes), a 180×180 apple-touch icon, and the tab title "Marquise". The production build check now fails without the title or either icon link. Supports #422.

## 2026-10-31

- Load real cinema directory and venue data in the approved interface. Keep screening queries fixed to the selected cinema.

## 2026-10-30

- Restore loaded browsing results and scroll position on Back, and keep title-search focus while URL-backed results update. Supports #336.

- Open the minimalist Screenings view on today in Montreal. Use the real API by default, separate catalogue search, persistent navigation, and direct movie metadata/schedule loading. Supports #333.

## 2026-10-20

### Changes

- Rebuild discovery, daily screenings, the searchable cinema directory and film routes around the injected paged discovery client. Keep dated cinema deep links and browser Back/Forward filters useful.
- Default daily listings to Montréal today, mark sample data as demo, distinguish missing films from temporary errors, and use actual cinema/movie page titles.
- Cover server filters, paging, history, cancellation, stale client/query results, preview controls, validation, retry and empty states with injected clients.
- Forward API-mode build variables through Turborepo and include them in its cache key so API builds cannot reuse a demo bundle.
- Verify critical layout and poster utility selectors in the production CSS during every interface build; consume the same source stylesheet in development and production.

## 2026-08-10

### Deployment

- **Screenings UI**: listings and details share consistent mock data, Montréal-aware dates and times, row-aware auto-fit pagination, mobile scrolling, accurate date selection, and a live current-time marker.

## 2026-08-08

### Changes

- **Restorable screenings URLs**: listing filters, selected date, pagination, card size, detail visibility, and filter-panel state are serialized in the URL. Movies now open on dedicated `/movies/<id>` routes, and browser Back restores the exact listings view.
- **Interface and deployment cleanup**: navigation now contains only `Screenings`; Fly.io deployment builds the pnpm workspace into an nginx static image with SPA route fallback, a health check, and one warm interface/API machine.

## 2026-08-05

### Changes

- **Landing page**: sticky header with the Marquise wordmark (logo top-left) and placeholder section nav ("À l'affiche", "Cinémas", "Films", "À propos"), plus a full-viewport `MovieGridController` — filter panel on the left, auto-paged movie grid filling the middle.
- **Data-source switching**: `VITE_MARQUISE_DATA_SOURCE=mock|api` (mock default). API mode targets same-origin `/v1/*`, proxied to the local API (`make api`) by the Vite dev server.
- **Source-level HMR**: the app aliases `marquise-components` and `marquise-client` to their source; component styles come from the package's prebuilt CSS bundle.

## 2026-07-29

### Changes

- **Remove hardcoded filter options**: `filterOptions.ts` deleted. `FilterBar` now receives `cinemas`, `genres`, `languages` as props derived from the full dataset, so every option stays visible regardless of active client-side filters.
- **`fetchMoviesByDate` per-date API fetching**: `PosterWallPage` only calls the API on date changes (`datesKey` stable dependency). All non-date filters (search, cinema, genre, lang, time range) are applied client-side via `useMemo`-wrapped `filterMovies` on the full cached dataset (`allMovies`), so toggling a filter is instant with no network round-trip.
- **Movie detail drawer and page**: lazy per-date screening fetches; standalone `/movie/:movieId` route with metadata loaded once then per-date screenings on date change.
- **Remove dead API functions**: `fetchMovies` and `fetchMovieDetail` — superseded by `fetchMoviesByDate`, `fetchMovieInfo`, and `fetchMovieScreenings`.
- **Replace `PosterWallSkeleton` with loading spinner**.
- **Date pills replace prev/next arrows** in detail views, with a "More dates" button (`fetchMovieDates`).
- **Wire detail views after library extraction**: wrappers connect `@marquise/components` detail views to the app-specific API and routing.
- **Remove "Live API" badge** and update the title to **"What's playing in Montréal"** with green-accented city name.

## 2026-07-19

### Changes

- **Fix Fly build failing to resolve workspace packages**: added `context = ".."` to `fly.toml` so the Docker build sees the full pnpm workspace.

## 2026-07-17

### Changes

- **Add Fly.io deployment**: Dockerfile (pnpm workspace build → static `nginx:alpine` serve) and `fly.toml` for app `marquise-interface`, with `VITE_API_BASE_URL=https://marquise-api.fly.dev` baked into the production build.
- **Replace per-movie-id N+1 fetch with `getByIds`**: poster-wall enrichment now calls `client.movies.getByIds()` in chunks of 100 ids.

## 2026-07-15

### Changes

- **Timezone handling for showtimes**: `formatShowtime`/`showtimeDateKey`/`resolveWindow` convert real UTC to Montréal wall-clock time via `Intl.DateTimeFormat` (`America/Toronto`), matching the corrected backend contract. Added `montrealDateKeyToUtcRange()` to resolve a Montreal calendar day to UTC bounds for `/v1/screenings` queries.
