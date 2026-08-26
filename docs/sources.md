# Showtime sources

How scrapers, adapters, and the registry fit together. Per-source detail lives
in module docstrings under `infrastructure/sources/<name>/`.

See also [architecture.md](architecture.md#key-patterns).

---

## Pattern

Each source has two sides:

1. **Scraper** (`packages/marquise-core/src/marquise/infrastructure/sources/<name>/`)
   — HTTP/API I/O, returns plain dict rows (`ShowtimeRow` shape).
2. **Adapter** (`packages/marquise-core/src/marquise/interface_adapters/repositories/source_adapters/<name>.py`)
   — implements `SourceAdapter` protocol; delegates to the scraper gateway.

The **registry** (`interface_adapters/repositories/source_registry.py`) maps source
names to adapter instances. The DI container registers adapters at startup.

Use cases call the registry — they never import scrapers directly.

---

## Current sources

| Name | Scraper | Adapter |
|------|---------|---------|
| `cineplex` | `infrastructure/sources/cineplex/` | `source_adapters/cineplex.py` |
| `cinemacinema` | `infrastructure/sources/cinemacinema/` | `source_adapters/cinemacinema.py` |
| `cinemapublic` | `infrastructure/sources/cinemapublic/` | `source_adapters/cinemapublic.py` |
| `cinestarz` | `infrastructure/sources/cinestarz/` | `source_adapters/cinestarz.py` |
| `cinemamoderne` | `infrastructure/sources/cinemamoderne/` | `source_adapters/cinemamoderne.py` |
| `cinematheque` | `infrastructure/sources/cinematheque/` | `source_adapters/cinematheque.py` |
| `outremont` | `infrastructure/sources/outremont/` | `source_adapters/outremont.py` |

All paths relative to `packages/marquise-core/src/marquise/`.

Showtimes must emit UTC ISO 8601 timestamps — use
`infrastructure/sources/_timezone.py` for Montreal-local sources.

---

## Adding a source

1. Add scraper under `infrastructure/sources/<name>/gateways/source.py`.
2. Add adapter under `interface_adapters/repositories/source_adapters/<name>.py`
   implementing `SourceAdapter` (see `base.py`).
3. Register in the DI container (`infrastructure/di/container.py`).
4. Unit-test the adapter with a mocked scraper gateway (`create_autospec`).
5. Add integration coverage only if the scraper needs real network validation.

Do not put HTTP or SQL in use cases or repository adapters.
