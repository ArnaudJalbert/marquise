# Marquise

Montreal cinema showtimes — aggregated, normalized, and queryable.

Marquise fetches showtime data from theater chains and independent cinemas across Montreal, normalizes it into PostgreSQL, and exposes it through a CLI, a REST API with public reads and authenticated screening writes, and a web interface.

Live API: [api.marquise.mov/docs](https://api.marquise.mov/docs)

## Development

Documentation lives in the repository (not all pages are published here):

| Document | Purpose |
|----------|---------|
| [Rules](https://github.com/ArnaudJalbert/marquise/tree/main/docs/agents/rules) | Architecture, naming, Python, testing, web and review rules |
| [Agent guide](https://github.com/ArnaudJalbert/marquise/blob/main/AGENTS.md) | Priorities, rule index and guide index |
| [Contributing](https://github.com/ArnaudJalbert/marquise/blob/main/CONTRIBUTING.md) | Setup, commands, paths, CI |

Additional guides (`docs/setup.md`, `docs/sources.md`, etc.) — see [AGENTS.md](https://github.com/ArnaudJalbert/marquise/blob/main/AGENTS.md#guides).
