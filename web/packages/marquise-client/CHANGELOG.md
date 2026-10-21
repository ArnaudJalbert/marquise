# Changelog

## 2026-10-20

### Changes

- Add `posterRenditionUrl`: known poster hosts get smaller renditions at read time. Cinéma Cinémas images route through their Cloudflare `/cdn-cgi/image/` resizer (originals ran to 60 MB); TMDB `original/` paths become `w500`. All other hosts pass through untouched.
- Add `DiscoveryClient` with requested-page screening filters, cinema name search and movie showtimes; HTTP requests accept cancellation signals and never drain paginated endpoints.
- Bound movie metadata enrichment to the current page's IDs and optional cinema website enrichment to one page. Preserve screening totals separately from grouped film counts.
- Make legacy HTTP grid/showtime collections explicitly first-page-only (100/48 screenings); use `DiscoveryClient` for complete navigation and totals. The deterministic demo client supports the same paging/filter protocol.
- Replace eager-pagination expectations with regression coverage for bounded pages, filters, grouping, metadata enrichment and cancellation signals.
- Convert local time filters correctly during daylight-saving transition mornings; reject skipped spring-forward times rather than silently shifting them.

## 2026-08-10

### Deployment

- **Shared HTTP and mock clients**: one client stack now powers both listings and movie details, with bounded request caching.

## 2026-08-08

### Changes

- **Movie detail data clients**: added HTTP and deterministic mock detail clients, movie IDs throughout the grid model, and shared date/showtime behavior between grid and detail views.

## 2026-08-05

### Changes

- **Data client for the REST API**: `HttpMovieGridClient` implements `MovieGridClient` — lists the upcoming days with screenings, paginates a date's screenings, bulk-fetches movie metadata (posters, genres, directors, duration) in chunks of 100, and resolves cinema websites for clickable cinema names. Empty base URL targets a same-origin API (dev proxy).
- **`MockMovieGridClient`**: deterministic seeded demo data (12-film catalogue, 4 Montréal cinemas) so the UI runs with zero backend.
- **Contract ownership moved out of `marquise-components`**: `Cinema`, `CinemaShowtime`, `MovieCardData`, `MovieCardGridItem` and `MovieGridClient` now live here; the components package re-exports them (dependency direction is now components → client).

## 2026-07-17

### Changes

- **Add `MoviesResource.getByIds`**: goes through `list()` with `ids` set and `size` forced to `ids.length` (satisfying the backend's `ids count <= size` constraint), unwrapping `.items` from the returned `Page`. `buildQuery` now serializes `string[]` values as repeated query params (`ids=a&ids=b`) to support it, and `ListMoviesParams` gained an `ids` field.
