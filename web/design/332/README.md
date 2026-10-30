# Minimalist catalogue prototype

## Plan before building

This is an Explore surface, a movie catalogue, not a landing page. Follow #331 and #332. Read Anthropic's official frontend-design skill at revision `ca45fc496a3436251f191354091d557da31c15b5`, then use claude-design only as supplementary guidance.

The posters carry the identity. White `#ffffff`, black `#000000`, border `#dddddd`, placeholder `#f2f2f2`, secondary text `#595959`. No accent colors outside original poster artwork. Choose Helvetica Neue with Arial fallback for compact, familiar film-programme typography, not a display headline. Body and controls 14px, titles 13px/18px, page headings 22px. Content max-width 960px, 24px desktop gutters, 16px mobile gutters. Grid gaps 24px desktop, 16px mobile. Poster ratio 2:3, object-fit cover. Titles occupy exactly two lines, full accessible names retained. Tiny visible arrow in a 44px hit target.

```
Marquise                    Movies  Cinemas
Search       Start date   End date
Today  Tomorrow  This weekend   Cinema / Language / Time
poster          poster          poster
small title  ↗  small title  ↗  small title  ↗
```

Below 640px, two columns. Search and dates remain visible. Other filters sit in a dismissible Filters panel. Desktop controls use native disclosure panels. No Apply button. Native date inputs supply calendars. No custom calendar dependency. Invalid date/time windows report an error, not a silent reinterpretation.

Preview is an anchored, bounded panel with at most three showtimes total, selected before grouping by cinema. Desktop mouse hover and explicit arrow open the same panel. Escape closes and returns focus to the arrow. Poster/title links remain separate. Detail has a small poster and compact metadata, then the full sample schedule grouped by date and cinema. Fixed-cinema pages reuse the grid without the cinema selector.

### Brief review

Rejected a large title and editorial introduction because home must start at controls and posters. Rejected alternate color themes and layout variants because the approved brief already fixes those axes. No hero, rails, sidebar, slider, decorative motion, badges, or promotional footer. The sample-state switcher is review tooling, visually separated below the catalogue, not proposed production UI.

## Baseline captured before implementation

`baseline.json` and `baseline-desktop.png` record a local production build from `bff353f51ee3f383997b91de81fed8e6edb5d51d`, with default MockMarquiseClient, on October 30, 2026. Routes: home, screenings, Dune detail, cinemas. No HTTP listing requests in mock mode. Only Dune has an external image in this fixture. Its resource transfer size is zero, which does not establish an image byte measurement or successful download.

`baseline-api.json` records the same old build compiled with `VITE_MARQUISE_DATA_SOURCE=api`. It captures real HTTP-client listing/detail/directory request URLs. No API was running, so these routes show error states. This is not a production dataset, controlled database integration run, deployed preview, or performance comparison. Do not infer performance budgets from these records.

## Run and review

From `web/`:

```sh
pnpm install --frozen-lockfile
pnpm prototype
# Open http://localhost:4174
```

The demo lives at `packages/components/demo`. Shared UI is exported from `marquise-components`, under `src/components/minimal`. The delivery app and existing clients are unchanged. The demo receives movies, cinema data, language choices, review dates and navigation through props. Fixtures and artwork are outside `src` and excluded from the library build. No dependencies were added.

For a local production preview, not a deployment:

```sh
pnpm build
pnpm prototype:build
pnpm --filter marquise-components exec vite preview --config demo/vite.config.ts --host 0.0.0.0 --port 4175
node packages/components/demo/check-isolation.mjs
```

Click Movies, Cinemas, any poster or title, a cinema name, and the preview arrow. Hover with a mouse over a poster, then move into its preview. The same panel appears with a touch tap or native keyboard Space activation. Escape closes previews or filter panels and restores focus. Filters update immediately. Open the state selector below the catalogue to review initial-loading, loading-more, empty and error/Retry. The final catalogue entry demonstrates absent poster and metadata. Booking links deliberately open example.com in another tab, not a real booking transaction.

The sample clock is fixed to the review date, rather than pretending these are today's live screenings. Multi-day fixture selection shows three preview screenings total before grouping. Detail pages show all four sample screenings even if listing controls exclude them. This ticket does not implement backend queries, infinite loading, async cancellation, full URL/history/cache restoration, title debounce, or a real complete-schedule API. Those remain dependent production work in #331.

## Verification and captures

`verification.log` contains the actual final command output. `pnpm build`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, and `pnpm prototype:build` passed. Tests passed in all packages: 59 client tests, 165 component tests including six new prototype behavior tests, and 24 delivery-app tests. The isolation checker passed across 32 library output files, including declarations and source maps. Some unchanged Turbo tasks used this worktree's build cache.

`browser-checks.json` records 46 successful Chromium checks through the browser harness. Checks exercised actual mouse hover, moving into the preview, native keyboard Space, Escape/focus, emulated touch taps, separate poster/title routing, cinema navigation, sample states, Retry, and missing metadata. Computed geometry proved three desktop columns, two mobile columns, 2:3 posters, 52px caption boxes, 44px arrow targets, popup bounds, and no horizontal overflow at 390px and 320px. Reduced-motion checks assert `animation-name: none` and `transition-property: none`, not an arbitrary duration budget.

`production-smoke.json` records a separate smoke check of the local built preview at port 4175. Home, movie, directory and fixed-cinema routes rendered without captured runtime errors or overflow. No listing HTTP or remote image requests were made by the prototype. All artwork is local. No API/database test was claimed or needed for this design-only ticket.

- [Desktop, 1280 × 1000](desktop.png) and [mobile, 390 × 844](mobile.png) are from the final local production build.
- [Desktop preview](desktop-preview.png), [desktop filters](desktop-filters.png), [mobile preview](mobile-preview.png), [mobile filters](mobile-filters.png), [movie detail](mobile-detail.png), [cinema directory](mobile-directory.png), [fixed cinema](mobile-cinema.png), and state screenshots are interaction captures from the local Vite demo.
- The baseline screenshot predates all prototype work. Baseline API mode had no running API, so its observed failures are not an integration benchmark.

The browser harness cannot provide visual image inspection here. Screenshot files and their dimensions were verified, and DOM/computed-style interactions were exercised, but the images have **not** received human visual approval. Browser checks are recorded review evidence, not a newly installed browser testing framework.

## Self-critique after rendering

The measured layout follows the catalogue brief without a landing-page introduction. Poster color is the only color outside neutrals. Long titles retain their full accessible name and occupy the same caption height as short titles. A compact visible arrow still gets a 44px touch target. The preview overlays its own poster rather than extending below the viewport, after the initial browser pass exposed why a below-card panel was a poor choice.

Tradeoffs to review with Arnaud:

- The panel obscures artwork while open, and mobile previews are narrow. Its content scrolls when necessary. A wider mobile sheet would be easier to read but would change the anchored-preview decision.
- Desktop and mobile share one Filters disclosure, with a horizontal filter group on desktop and stacked groups on mobile. This is leaner than separate cinema/language popovers, but adds a click on desktop. Search, dates and shortcuts stay visible.
- The fixed 2:3 crop may crop artwork that has another native ratio. The prototype uses `object-fit: cover`; approval should explicitly confirm that tradeoff.
- Only three local artwork fixtures were available from successful downloads. Failed sources were removed rather than leaving broken requests. The other three entries intentionally show the missing-poster treatment, which overrepresents this state compared with a healthy catalogue.
- Native date/time controls inherit browser rendering. The geometry checks cover Chromium, not Safari/iOS or a screen reader. No visual aesthetic judgment is claimed from DOM checks.

The design self-audit found no hero, accent hue, decorative illustration, icon tiles, blur, statistic blocks or rail. Helvetica is an intentional compact programme-list choice, but it is restrained rather than distinctive. The posters, not typography, provide the identity.

## Review and approval

This branch is a design proposal. Arnaud's explicit approval is **pending**. Dependent production implementation must not begin on the basis of this prototype alone. Nothing is deployed and the existing delivery interface is unchanged.
