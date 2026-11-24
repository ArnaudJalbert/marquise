# Showtime sources

How scrapers, adapters, and the registry fit together. Per-source detail lives
in each `infrastructure/sources/<name>.py` module docstring.

See also the [architecture rules](agents/rules/architecture.md).

---

## Pattern

Each source has two sides:

1. **Scraper** (`packages/marquise-core/src/marquise/infrastructure/sources/<name>.py`)
   — HTTP/API I/O, returns plain dict rows (`ShowtimeRow` shape).
2. **Adapter** (`packages/marquise-core/src/marquise/interface_adapters/repositories/source_adapters/<name>.py`)
   — implements `SourceAdapter` protocol; delegates to the scraper gateway.

The **registry** (`interface_adapters/repositories/source_registry.py`) maps source
names to adapter instances. Dedicated wiring in
`infrastructure/di/source_registry.py` registers adapters at startup.

Use cases call the registry — they never import scrapers directly.

---

## Current sources

| Name | Scraper | Adapter |
|------|---------|---------|
| `cineplex` | `infrastructure/sources/cineplex.py` | `source_adapters/cineplex.py` |
| `cinemacinema` | `infrastructure/sources/cinemacinema.py` | `source_adapters/cinemacinema.py` |
| `cinemapublic` | `infrastructure/sources/cinemapublic.py` | `source_adapters/cinemapublic.py` |
| `cinestarz` | `infrastructure/sources/cinestarz.py` | `source_adapters/cinestarz.py` |
| `cinemamoderne` | `infrastructure/sources/cinemamoderne.py` | `source_adapters/cinemamoderne.py` |
| `cinematheque` | `infrastructure/sources/cinematheque.py` | `source_adapters/cinematheque.py` |
| `outremont` | `infrastructure/sources/outremont.py` | `source_adapters/outremont.py` |

All paths relative to `packages/marquise-core/src/marquise/`. The `tmdb*.py` files beside them are movie metadata providers, not showtime sources ([docs/providers/tmdb-metadata.md](providers/tmdb-metadata.md)).

Showtimes must emit UTC ISO 8601 timestamps — use
`infrastructure/sources/_timezone.py` for Montreal-local sources.

---

## Adding a source

1. Add scraper as `infrastructure/sources/<name>.py`.
2. Add adapter under `interface_adapters/repositories/source_adapters/<name>.py`
   implementing `SourceAdapter` (see `base.py`).
3. Register in `infrastructure/di/source_registry.py`.
4. Unit-test the adapter with a mocked scraper gateway (`create_autospec`).
5. Add integration coverage only if the scraper needs real network validation.

Do not put HTTP or SQL in use cases or repository adapters.
