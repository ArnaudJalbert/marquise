# October 30, 2026 cleanup verification

The cleanup starts from PR #339 head `b0a5d13ed8b2b65369537938a071bfc8ddd44fb2` and includes the interactive session edits plus the subsequent code review fixes. The resulting commit is linked by PR #339. These checks concern the local code and built artifacts, not a deployment.

## Checks

All commands ran from `web/` in the isolated PR worktree.

| Command | Result |
| --- | --- |
| `pnpm lint -- --threads=2` | All three packages pass, zero warnings/errors |
| `pnpm typecheck` | All three packages pass |
| `pnpm test -- --maxWorkers=2` | Full workspace run passes: client 61, components 173, interface 24 |
| `pnpm --filter marquise-components test --maxWorkers=2` | Final affected-package rerun passes 174 tests after the last same-ID metadata regression; current total is 259 |
| `pnpm build` | All three packages build; production layout/style checker passes |
| `pnpm prototype:build` | Demo TypeScript check and Vite build pass |
| `node packages/components/demo/check-isolation.mjs` | Fixture isolation passes across 36 library output files |
| `git diff --check` | Passes |

The first unconstrained workspace lint attempt ended with exit 137 in the unchanged interface package. Retrying the same lint rules with two worker threads per process passed. The test run was uncached; some dependency builds in later commands reused local Turbo cache.

The prototype suite now has 15 behavior tests. New cases prove persistent section links, independent catalogue/screening results, one-date navigation with four-day request bounds, cancellation after switching movies, initial schedule loading/Retry, both handles' fixed range and floor/clamping behavior, matching applied hour filters, active movie navigation, poster recovery after a failed image, and schedule loading after same-ID metadata replaces cached screenings. Client tests prove a single catalogue page and an exact-ID inclusive Montréal date window across the autumn daylight-saving transition.

## Review

Independent review found mismatched displayed/applied fractional-hour filters and a catalogue poster path bypassing the existing rendition helper. Both were corrected with regression coverage. The cleanup also wraps the schedule toolbar, keeps the movie-detail navigation active, and resets failed detail posters when the movie changes. The code extraction preserves injectable data and callbacks; HTTP remains in the client package.

## Limits

- No new real-browser geometry, interaction, or screenshot run was performed for the cleanup. Existing screenshots and browser records are historical; they are not current-head evidence. Mobile wrapping and filter positioning still need a current browser pass during #338.
- No live API/database integration or production deployment was performed. HTTP tests use injected fake fetch responses.
- The prototype catalogue loads all pages for local title search. It is explicitly documented as a dev-only shortcut; #336 requires bounded endpoint pagination/search for production.
- Sample screening fixtures remain separate from optional local API catalogue data. Fallback is labeled. All normal sample films have local posters; the Perfect Days asset was corrected from its distributor and inspected locally.

## Follow-up: self-contained sample API

The recurring showtime failure was reproduced against the actual dev server: the request to `/v1/screenings` returned HTTP 502 because it was proxied to an absent localhost:8000 backend while the UI displayed fictional sample movie IDs.

The prototype now serves its fixture catalogue and screenings through local REST endpoints by default on both the Vite dev and built-preview servers. Real-backend mode is explicit through `VITE_MARQUISE_DATA_SOURCE=api`; it preserves genuine failure handling. Server and client mode resolution both honor Vite environment values.

- The original failing four-day request now returns 100 screenings, exactly 25 per Montréal day across the DST transition, on both dev and preview servers.
- `/v1/movies` returns all six normal sample films with posters.
- Four additional offline tests exercise the real typed HTTP client and demo adapter against the sample responses: catalogue loading, all 350 screenings over four API pages, requested/empty date windows, and catalogue search/paging. The affected component/demo suite passes 178 tests; current workspace total is 263.
- Demo typecheck, production demo build, demo lint, and library fixture isolation pass. Imports in the server config have explicit extensions and the dev-only TypeScript config permits them.
- Independent review checked the approach and found two configuration issues, mismatched `.env` mode resolution and TypeScript extension settings. Both are corrected.

No live backend or new browser interaction run is claimed. These checks establish the local sample server and HTTP path.
