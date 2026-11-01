# Changelog

## 2026-11-01

- Replace Terms and Privacy layout placeholders with review drafts; clarify source non-affiliation, TMDB credits, public API reuse, server logging, and the privacy contact.

- Carry TMDB scores and vote counts for film detail metadata.


## 2026-10-31

- Preserve appended cinema results on Back and exclude already-started screenings from movie schedule requests. Remove redundant schedule state and date-window checks.

- Complete cinema directory and venue pages with address, website, loading, error, retry, and fixed-cinema listings.
- Load the complete movie schedule window on entry, keep date navigation usable during requests, and discard results from earlier windows.

## 2026-10-30

- Automatically append Screenings and Movies pages, retain loaded cards with Retry after failures, and preserve filtered Screenings pages when returning from a movie. Supports #336.

- Show the shared Screenings filters in production. Keep selections in the URL, debounce title search, and apply server-filtered movie-first results. Supports #335.

- Connect the approved minimal UI through an injected production browse client. Keep catalogue and screening requests independent, show initial loading/error/Retry, and share one active preview across cards. Supports #333.

### Changes

- Serve dev-only movies and screening fixture endpoints in the prototype dev/preview server by default, so showtime navigation works without a backend. Keep real API mode explicit and visibly labeled.
- Apply the approved separate Screenings, Movies, and Cinemas views, floating below-card previews, four-column grid, collapsed section descriptions, compact filter overlay/footer, and shared-scale daily hour slider.
- Isolate movie schedule state with one-day navigation, one-to-four-day windows, date columns or cinema rows, independent cinema/language filters, stale-request cancellation, and Retry. Keep API catalogue results separate from sample screenings.
- Add the proposed minimalist catalogue components with bounded poster titles, separate pointer/keyboard/touch previews, movie schedules and fixed-cinema browsing. Existing production routes remain unchanged; Arnaud approved the prototype design in #332 on October 30.
- Add a local React review demo outside the library build, sample-state controls, baseline evidence, desktop/mobile captures and a design decision record under `web/design/332`.

## 2026-10-20

### Changes

- Add shared `MarquiseExperience`, poster carousels from page-local movie genres, daily server-filter controls, cinema search and film pages. Components receive clients and navigation through props.
- Add poster-only cards with portalled hover previews and explicit keyboard/touch controls; preserve tickets, movie links, responsive layout, focus and reduced-motion support. Reserve image dimensions and keep title fallbacks.
- Cancel superseded page requests, suppress stale results when queries or clients change, and show specific time-range validation, loading, retry, empty and movie-not-found states. Existing grid/detail exports remain available.

## 2026-08-10

### Deployment

- **UI primitives**: native selects and Radix primitives replace custom calendar, popover, and hover behavior; duplicate demos and unused UI primitives removed.

## 2026-08-08

### Changes

- **Screenings grid controls and cards**: display controls moved below the grid with details on the left, pagination centered, and card size on the right. Cards retain centered titles when details are hidden, use consistent row sizing, and show an accessible bordered showtimes expansion with a close button.
- **Montréal-aware filtering**: today's time range starts at the current hour, future dates reset to all day, and returning to today reapplies the current-hour filter.

## 2026-08-05

### Changes

- **Interactive movie grid filters**: `MovieFilterPanel` (date picker, cinema/genre/language chip groups, start/end time-range slider, optional card-size slider and details toggle), `useMovieFilters` (fetches dates + one selected date, filters applied locally), and pure `movie-grid-filter.ts` logic wired together by `MovieGridController`.
- **Per-date movie detail page**: `MovieDetailPage` renders one showtime column per date; columns slide left/right, adapt to the container width, and each date's showtimes are fetched lazily as its column comes into view. Adds a `Popover` UI primitive and the `movie-detail-client` / `movie-grid-client` data-source protocols.
- **Card presentation options**: `MovieCard` poster-only mode (`hideDetails`) and a card-size auto-fit path in `MovieCardGrid` (up to 6 columns default; 8 with an explicit `cardSize`).
- **Robustness fixes from code review**: stale in-flight showtimes no longer overwrite the cache after a movie change; the fetch-error banner clears once a failed date recovers; per-date Retry no longer reloads the dates list; and a collapsed time-range slider can now be expanded by dragging its start thumb. 126 tests passing.

## 2026-08-04

### v0.1.0 (new)

- **Component library**: pnpm workspace package (`marquise-components`) ships a prebuilt CSS bundle (`dist/index.css`) so consumers do not need their own Tailwind install.
- **`MovieCard`**: poster, title, meta, flat showtime chips and a cinema-grouped all-showtimes view shared between a hover popover and an inline widget (single HoverCard root, no DOM duplication or hover flicker). `MoviePoster` lazy-loads images at low priority with a loading bar and graceful error fallback.
- **`MovieCardGrid`**: responsive grid with numeric or `"auto"` pagination; auto mode measures its container (ResizeObserver) and row height (max across the first row), re-measuring on any resize, and pages so nothing overflows a bounded-height parent.
- **`CinemaShowtimeGroups` + `groupByCinema`**: single-pass, O(n) grouping reused across the popover, the inline widget, and the grid.
- **Accessibility**: `aria-expanded`/`aria-controls`, `aria-live` page indicator, keyboard paging on a focusable grid, crossed-out started showtimes, hover-card enter/exit animations.
- **Tooling**: Vite 8 library build with all runtime deps externalized, TypeScript strict (`noUncheckedIndexedAccess`), oxlint, Vitest 4 + Testing Library (43 tests), and a dev-only demo page (`make web-demo`).

## 2026-07-29

### v0.2.0

- **Move detail views into the library**: `MovieDetailDrawer`, `MovieDetailPage`, `detailTypes`, `detailUtils`, and `timezone` moved from `marquise-interface` for reusability. Components accept API functions as props with no dependency on `react-router-dom`.
- **Date picker arrows**: `<` and `>` buttons next to the calendar icon for quick day-to-day navigation.
- **Past-showtime strikethrough**: showtimes in the past (`showtime` ISO datetime) are rendered with `line-through` and reduced opacity in detail views.
- **Default time range to current hour**: the time-range slider starts at the current hour (`new Date().getHours()`) for today, and resets to `0–24` (full day) when navigating to a future or past date.
- **Disable past dates in calendar**: calendar cells for dates before today are visually muted and unclickable.
- **Midnight–midnight range**: time range slider spans `0–24` instead of `8–24` to cover late-night screenings.
- **Replace "Multiple" with "Single" mode**: the date picker now offers Single / Range instead of Multiple / Range. Single mode replaces the selection on click (no toggle).

## 2026-07-15

### Changes

- **Move `filterMovies` filter/sort/dedup logic into the library**: extracted `filterMovies.ts` from `marquise-interface` so the AND-filter semantics (cinema, genre, date, language, time range, search text) and `mergeByTitle` cross-cinema dedup can be reused — and tested — in one place.
- **Add `addDaysToDateKey`**: shared date-key arithmetic replaces an identically implemented private function in the interface app.
- **Fix `PosterImage` render-time side effect**: replaced a `useState` + render-time mutation pattern with a canonical `useEffect` that resets the error state when `src` changes.
- **Add test infrastructure**: `vitest`, `jsdom`, and `@testing-library/react`; 30 unit tests across 5 test files.
