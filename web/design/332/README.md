# Minimalist catalogue prototype

Arnaud approved the interactive design in PR #339 on October 30, 2026. The [decision record](decisions.md) captures the final design; issues #331 through #338 carry production requirements. The production interface is unchanged by this prototype.

## Run

From `web/`:

```sh
pnpm install --frozen-lockfile
pnpm prototype
# http://localhost:4174
```

The dev-only demo is `packages/components/demo`. Shared UI is exported by `marquise-components`; HTTP is supplied by `marquise-client`. Fixtures and local artwork are excluded from the library build.

The three sections are separate views: Screenings, Movies, and Cinemas. Poster/title links open movie detail; the arrow or mouse hover opens a compact preview below the card. Movie schedules show up to four dates, advance one day at a time, and offer date columns or cinema rows. Section descriptions and examples are collapsed.

For a local built artifact:

```sh
pnpm build
pnpm prototype:build
node packages/components/demo/check-isolation.mjs
```

## Data and limits

- Screening fixtures use the review date October 30, 2026. Dune has 350 screenings across 14 days and seven cinemas; Jesse James has one. All six normal fixtures have local posters, with [recorded sources](../../packages/components/demo/public/posters/SOURCES.md). Sample booking links open example.com.
- By default, the Vite dev and built-preview servers serve `GET /v1/movies` and `GET /v1/screenings` from the sample fixtures. Date navigation still makes real HTTP requests through the typed client, without requiring a separate backend. Empty dates beyond the fixture window return an empty result, not a failed request.
- To use a running backend at localhost:8000 for Movies and date navigation, start with `VITE_MARQUISE_DATA_SOURCE=api pnpm prototype`. Server and client use the same resolved mode, including Vite environment files. Screenings remains a design fixture grid; use actual catalogue movie IDs when reviewing API schedules. Real API errors remain visible.
- Movie date navigation uses exact movie IDs and inclusive Montréal calendar-day bounds, requests every page in that window, and ignores/cancels obsolete responses. A catalogue movie without cached screenings loads its initial schedule.
- The prototype's catalogue search loads all movie pages. This is a documented dev-only shortcut, not the production pagination contract. #336 requires endpoint search and bounded append.
- Sample-state controls remain review tooling. This branch does not implement the production movie-first query, complete browser-history/scroll restoration, production catalogue pagination, or backend changes.

## Current verification

See [session verification](session-verification.md) for the cleanup checks and their limits. New regression tests cover section navigation, separate catalogue/screening data, one-day windows, stale responses, initial schedule retry, slider semantics, and typed API queries.

## Historical evidence

The existing `baseline*.json`, screenshots, `browser-checks.json`, `production-smoke.json`, `verification.log`, and `provenance.sha256` predate the interactive review and cleanup. They remain historical evidence of the earlier prototype, not assertions about the current revision.

Those earlier records showed three desktop columns, previews over posters, and missing artwork. The approved design supersedes those choices with four columns, below-card previews, and populated normal fixture posters. Do not use the older geometry, screenshots, test counts, or claim of pending approval as current evidence.

The API baseline was recorded without a running backend. Neither the old baseline nor this local prototype establishes production integration, deployed behavior, or a performance improvement.
