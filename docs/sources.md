# Showtime sources

How scrapers, adapters, and the registry fit together. Per-source detail lives
in each `infrastructure/sources/<name>.py` module docstring.

See also the [architecture rules](agents/rules/architecture.md).

---

## Pattern

Each source has two sides:

1. **Scraper** (`packages/marquise-core/src/marquise/infrastructure/sources/<name>.py`)
   — HTTP/API I/O, returns plain dict rows (`ShowtimeRow` shape).
2. **Adapter** (`packages/marquise-core/src/marquise/interface_adapters/sources/<name>.py`)
   — implements `SourceAdapter` protocol; delegates to the scraper gateway.

The **registry** port is `SourceRegistry` in `application/sources/`, beside
`ShowtimeRow` and `MovieEnrichmentData`. `ScraperSourceRegistry`
(`interface_adapters/sources/scraper_source_registry.py`) implements it and maps
source names to adapter instances. Dedicated wiring in
`infrastructure/di/source_registry.py` registers adapters at startup.

Use cases call the `SourceRegistry` port — they never import scrapers directly.

---

## Current sources

| Name | Scraper | Adapter |
|------|---------|---------|
| `cineplex` | `infrastructure/sources/cineplex.py` | `interface_adapters/sources/cineplex.py` |
| `cinemacinema` | `infrastructure/sources/cinemacinema.py` | `interface_adapters/sources/cinemacinema.py` |
| `cinemapublic` | `infrastructure/sources/cinemapublic.py` | `interface_adapters/sources/cinemapublic.py` |
| `cinestarz` | `infrastructure/sources/cinestarz.py` | `interface_adapters/sources/cinestarz.py` |
| `cinemamoderne` | `infrastructure/sources/cinemamoderne.py` | `interface_adapters/sources/cinemamoderne.py` |
| `cinematheque` | `infrastructure/sources/cinematheque.py` | `interface_adapters/sources/cinematheque.py` |
| `outremont` | `infrastructure/sources/outremont.py` | `interface_adapters/sources/outremont.py` |

All paths relative to `packages/marquise-core/src/marquise/`. The `tmdb*.py` files beside them are movie metadata providers, not showtime sources ([docs/providers/tmdb-metadata.md](providers/tmdb-metadata.md)). Their adapter is `interface_adapters/metadata/tmdb.py`.

Showtimes must emit UTC ISO 8601 timestamps — use
`infrastructure/sources/_timezone.py` for Montreal-local sources.

---

## Adding a source

1. Add scraper as `infrastructure/sources/<name>.py`.
2. Add adapter under `interface_adapters/sources/<name>.py`
   implementing `SourceAdapter` (see `base.py`).
3. Register in `infrastructure/di/source_registry.py`.
4. Unit-test the adapter with a mocked scraper gateway (`create_autospec`).
5. Add integration coverage only if the scraper needs real network validation.

Do not put HTTP or SQL in use cases or repository adapters.
