# Changelog

## 2026-08-18

### v0.1.4

- **Migrate cinema deletion to direct use-case execution**: `marquise cinema delete` now executes `DeleteCinemaUseCase` directly and always shuts down its factory. Closes #165.

### v0.1.3

- **Migrate cinema creation to direct use-case execution**: `marquise cinema create` now executes `CreateCinemaUseCase` directly and optionally assigns a source after creation. Closes #163.

## 2026-08-14

### v0.1.2

- **Replace Typer with argparse**: `cinema`, `source`, and `import` commands now use stdlib `argparse`; interactive prompts continue through `questionary`. Closes #161.

## 2026-08-03

### v0.1.1

- **Remove the `auth` command group**: `marquise auth login|logout|status` is gone (`auth_commands.py` deleted, unwired from `app.py`). "(admin only)" docstrings and the `_select_cinema_admin` helper were cleaned up accordingly.

## 2026-07-15

### v0.1.0

- **Extract CLI into a workspace package**: CLI code moved to `apps/marquise-cli/` with `MarquiseFactory`. Closes #105, #106.
