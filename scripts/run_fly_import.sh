#!/usr/bin/env bash
set -euo pipefail

: "${FLY_IMAGE:?FLY_IMAGE is required}"
: "${DAYS:?DAYS is required}"

export NO_COLOR=1
set +e
machine_output=$(flyctl machine run "$FLY_IMAGE" \
  --app marquise-db --region yyz --restart no \
  -- import all --days "$DAYS" 2>&1)
run_status=$?
set -e
printf '%s\n' "$machine_output"

machine_id=$(sed -n 's/.*Machine ID: //p' <<<"$machine_output" | tail -n 1)
if [[ -z "$machine_id" ]]; then
  echo "Fly did not return a Machine ID; cannot monitor or clean up the import Machine" >&2
  ((run_status != 0)) && exit "$run_status"
  exit 1
fi

cleanup() {
  local status=$?
  trap - EXIT
  if ! flyctl machine destroy --app marquise-db --force "$machine_id"; then
    echo "Failed to destroy temporary Fly Machine $machine_id" >&2
    ((status != 0)) || status=1
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

deadline=$((SECONDS + 5400))
while :; do
  machine_status=$(flyctl machine status "$machine_id" --app marquise-db)
  if grep -q 'State: stopped' <<<"$machine_status"; then
    break
  fi
  if ((SECONDS >= deadline)); then
    echo "Timed out waiting for temporary Fly Machine $machine_id" >&2
    exit 1
  fi
  sleep 5
done

flyctl logs --app marquise-db --machine "$machine_id" --no-tail
exit_code=$(sed -nE 's/.*exit_code=(-?[0-9]+).*/\1/p' <<<"$machine_status" | tail -n 1)
if [[ -z "$exit_code" ]]; then
  echo "Fly did not report an exit code for Machine $machine_id" >&2
  exit 1
fi
if ((exit_code < 0)); then
  echo "Fly could not determine the process exit code for Machine $machine_id" >&2
  exit 1
fi
if ((exit_code != 0)); then
  echo "Import Machine $machine_id exited with status $exit_code" >&2
fi
if ((run_status != 0 && exit_code == 0)); then
  exit "$run_status"
fi
exit "$exit_code"
