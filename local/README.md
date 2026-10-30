# Isolated local stack

Run the real React app, FastAPI API, and PostgreSQL together without production
services or credentials. This uses the implementation from #333, not the prototype
or sample API. The containers, network and database volume belong to the
`marquise-local` Compose project. Every host port binds to 127.0.0.1.

From the repository root, with Docker running:

```sh
make local-up
```

Open [the React app](http://localhost:4300) or [API docs](http://localhost:8300/docs).
Postgres listens on `127.0.0.1:54330`, database/user `marquise_local`, password
`local-only`. This fixed credential is only for this disposable local environment.
No `.env` file is needed or loaded. The API receives an explicit local database URL.
The React build copies source and build config explicitly, excluding env files.
The app sends same-origin `/v1/*` requests through local nginx to the local API.

```text
localhost:4300  React + nginx
                   /v1/*
                api:8000
                   │
                db:5432  ← localhost:54330
```

The first build downloads container images and locked package dependencies.
Runtime browsing needs no external API, Supabase account, TMDB key, or production
access. Protected write endpoints have no configured authentication provider.

## Data

This is real PostgreSQL with controlled test rows. Film names and local artwork
are recognizable, but all schedules and booking links are fictional. The API does
not manufacture responses or switch to fixtures when it fails.

- 53 real, named catalogue movies, all with local poster artwork. The catalogue
  fills two pages of 24 and has a third page with five movies.
- Dune: Part Two has 25 screenings per day for 14 Montreal days, 350 total, with
  source language acronyms across seven cinemas. Each local day converts to UTC
  independently, including DST transitions.
- Perfect Days has one screening tomorrow. Arrival has none, and uses an opaque
  ID with a slash. Fifty other films exercise catalogue pages and poster grids,
  with sparse metadata and the long title The Assassination of Jesse James by
  the Coward Robert Ford.
- Posters mount from the existing dev-only artwork directory. Its
  [source record](../web/packages/components/demo/public/posters/SOURCES.md)
  applies. They are not copied into the local React image or production bundle.

`make local-up` refreshes generated screening dates to today after startup.
`make local-seed` does the same without rebuilding. Reseeding replaces only IDs
starting `local-screening-`; it preserves other screening rows. Cinema/movie
fixtures insert only if their IDs are absent. Treat those prefixes as reserved
for test data. Up and down preserve the named volume `marquise-local_database`.

## Commands

| Command | What it does |
| --- | --- |
| `make local-up` | Build the current code, start all three services, wait for health, refresh test dates |
| `make local-status` | Show services and health |
| `make local-logs` | Follow recent logs |
| `make local-seed` | Refresh generated test schedules, keep non-fixture data |
| `make local-down` | Stop/remove containers and network, keep the database volume |

Rerun `make local-up` after source edits to rebuild. This serves a built React
artifact, not a hot-reload server. Production Dockerfiles, Fly configuration and
the existing Compose file are unchanged.

To inspect local rows:

```sh
docker compose --env-file /dev/null -p marquise-local -f compose.local.yml \
  exec db psql -U marquise_local -d marquise_local
```

If a reserved port is already used, stop the other local service or change the
binding in `compose.local.yml`. Do not point this configuration at production.

## Verification

On October 30, 2026, `make local-up` built the actual API and React image and
reported all three services healthy. `make local-seed` repeated successfully.
Postgres contained 53 movies, seven cinemas, and 377 screenings after reseeding.
The API returned 24 distinct screening cards on page one and the shorter second
page, plus all three catalogue pages with 53 movies and working posters.

```sh
uv run --with playwright python scripts/verify_local_stack.py
```

The check passed with Chromium 156.0.8078.4. It queried every page of all 53
catalogue movies, loaded each poster, and queried every page of the 350-show
Dune window, asserted 25 per day across 14 days and seven cinemas, and exercised
the actual React catalogue. Scrolling to the end appended each page in Screenings
and Movies. Opening a movie from the bottom of the catalogue and using Back
restored all 53 cards and the measured scroll position. The check also covered
combined title/cinema/language/hour filters, dense detail, and the catalogue-only
slash-ID route including refresh. It opened the filter panel at desktop and mobile
sizes, checked that it does not shift the controls or grid, and moved both time
handles with keyboard, mouse, and touch input. All 24 browser API requests stayed
on the local app's origin. No HTTP request was mocked or intercepted. It writes
local screenshots to `/tmp/marquise-local-stack/dense-schedule.png` and
`/tmp/marquise-local-stack/movies-all-pages.png`.

The local preview now includes the #333 listing, #335 screening filters, and #336
bounded append and Back restoration. Cinema browsing remains in progress.
This stack does not prove live provider data, Safari, protected writes, or
deployment behavior.
