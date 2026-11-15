#!/usr/bin/env bash
# Claude Code Stop hook: an agent worker cannot end its turn while the checks
# CI runs on its change fail. Exit 2 blocks the stop and shows stderr to the agent.
# Only agent worktrees under ~/.t3/worktrees/ are checked; Arnaud's own
# sessions and branches without changes stop freely.
set -uo pipefail

cwd=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd", ""))' 2>/dev/null)
root=$(git -C "${cwd:-.}" rev-parse --show-toplevel 2>/dev/null) || exit 0
case "$root" in "$HOME"/.t3/worktrees/*) ;; *) exit 0 ;; esac
cd "$root" || exit 0

base=$(git merge-base origin/main HEAD 2>/dev/null) || exit 0
changed=$( { git diff --name-only "$base"; git ls-files --others --exclude-standard; } | sort -u)
[ -n "$changed" ] || exit 0

run() {
  local output
  if ! output=$("$@" 2>&1); then
    printf 'Stop hook: `%s` failed. Fix it before finishing.\n%s\n' "$*" \
      "$(tail -n 60 <<<"$output")" >&2
    exit 2
  fi
}

if grep -qvE '^web/' <<<"$changed"; then
  run uv run ruff format --check .
  run uv run ruff check .
  run uv run ty check packages/marquise-core/src
  # Both apps import core, so a core change runs every suite.
  core=$(grep -c '^packages/' <<<"$changed")
  [ "$core" -gt 0 ] && run uv run pytest -q \
    packages/marquise-core/tests/unit_tests/
  if [ "$core" -gt 0 ] || grep -q '^apps/marquise-api/' <<<"$changed"; then
    run uv run pytest -q apps/marquise-api/tests/
  fi
  if [ "$core" -gt 0 ] || grep -q '^apps/marquise-cli/' <<<"$changed"; then
    run uv run pytest -q apps/marquise-cli/tests/
  fi
fi
if grep -q '^web/' <<<"$changed"; then
  run pnpm -C web lint
  run pnpm -C web typecheck
  run pnpm -C web test
fi
exit 0
