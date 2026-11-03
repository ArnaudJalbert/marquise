#!/usr/bin/env python3
"""Deterministic daily post-import reliability review for Marquise."""

from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REPO = "ArnaudJalbert/marquise"
WORKFLOW = "scheduled-import.yml"
API_BASE = "https://api.marquise.mov"
TRACE_PATH = Path("/opt/data/profiles/mara/state/latest-import-review.json")
GH = "/opt/data/bin/gh"


def gh_json(args: list[str]) -> dict | list:
    result = subprocess.run(
        [GH, *args], capture_output=True, text=True, check=True, timeout=30
    )
    return json.loads(result.stdout)


def api_json(path: str) -> dict:
    with urllib.request.urlopen(API_BASE + path, timeout=20) as response:
        return json.load(response)


def read_trace() -> dict:
    try:
        return json.loads(TRACE_PATH.read_text())
    except FileNotFoundError:
        return {"schema_version": 1, "workflow": WORKFLOW, "last_handled_run": None}


def write_trace(run: dict, handling: str) -> None:
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACE_PATH.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "workflow": WORKFLOW,
                "last_handled_run": {
                    "run_id": run["databaseId"],
                    "status": run["status"],
                    "conclusion": run["conclusion"],
                    "workflow_url": run["url"],
                    "reviewed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "handling": handling,
                },
            },
            indent=2,
        )
        + "\n"
    )


def fetch_window(start: date, end: date) -> list[dict]:
    query = urllib.parse.urlencode(
        {"from": start.isoformat(), "to": end.isoformat(), "size": 100}
    )
    first = api_json("/v1/screenings?" + query)
    items = list(first.get("items", []))
    for page in range(2, int(first.get("pages", 1)) + 1):
        items.extend(api_json(f"/v1/screenings?{query}&page={page}").get("items", []))
    return items


def main() -> int:
    runs = gh_json(
        [
            "run",
            "list",
            "--repo",
            REPO,
            "--workflow",
            WORKFLOW,
            "--limit",
            "1",
            "--json",
            "databaseId,status,conclusion,url,updatedAt,workflowName",
        ]
    )
    if not runs:
        print(
            "Severity: high\n"
            "User impact: no scheduled import run was found.\n"
            "Verification status: blocked"
        )
        return 0

    run = runs[0]
    trace = read_trace().get("last_handled_run") or {}
    unchanged_final = (
        str(trace.get("run_id")) == str(run["databaseId"])
        and trace.get("status") == run["status"]
        and trace.get("conclusion") == run["conclusion"]
        and run["status"] == "completed"
    )
    if unchanged_final:
        print("[SILENT]")
        return 0

    print(f"CI run: {run['databaseId']} — {run['url']}")
    print(
        f"CI status: {run['status']}; conclusion: {run['conclusion']}; "
        f"updated: {run['updatedAt']}"
    )

    if run["status"] != "completed" or run["conclusion"] != "success":
        print("Severity: high")
        print(
            "User impact: the latest import did not complete successfully; "
            "imported data was not reviewed."
        )
        print(
            "Evidence: the exact scheduled-import run above is non-successful "
            "or non-final."
        )
        print(
            "Recommended action: inspect the failed or still-running GitHub Actions "
            "job before trusting showtimes."
        )
        print("Verification status: final-blocked")
        write_trace(run, "final-blocked")
        return 0

    today = datetime.now(UTC).date()
    window_end = today + timedelta(days=6)
    try:
        items = fetch_window(today, window_end + timedelta(days=1))
        health = api_json("/health").get("status")
    except Exception as exc:
        print("Severity: high")
        print(
            "User impact: imported data could not be verified through the public API "
            f"({type(exc).__name__})."
        )
        print(
            "Recommended action: retry the API review; do not treat CI success as "
            "data-review success."
        )
        print("Verification status: blocked")
        write_trace(run, "final-blocked")
        return 0

    natural_keys = [
        (x.get("cinema_id"), x.get("movie_id"), x.get("showtime")) for x in items
    ]
    ids = [x.get("id") for x in items]
    duplicate_ids = sum(n - 1 for n in Counter(ids).values() if n > 1)
    duplicate_keys = sum(n - 1 for n in Counter(natural_keys).values() if n > 1)
    required = ["id", "movie_id", "movie_title", "cinema_id", "cinema_name", "showtime"]
    missing = {
        field: sum(not str(x.get(field, "")).strip() for x in items)
        for field in required
    }
    malformed_urls = [
        x
        for x in items
        if x.get("ticket_url")
        and urllib.parse.urlparse(x["ticket_url"]).hostname in {None, "en"}
    ]
    bad_timestamps = []
    for item in items:
        try:
            datetime.fromisoformat(str(item["showtime"]).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            bad_timestamps.append(item)

    anomalies = []
    if duplicate_ids or duplicate_keys:
        anomalies.append(
            f"duplicates: {duplicate_ids} duplicate IDs, "
            f"{duplicate_keys} duplicate natural keys"
        )
    if any(missing.values()):
        anomalies.append(f"missing required fields: {missing}")
    if malformed_urls:
        anomalies.append(f"malformed ticket URLs: {len(malformed_urls)}")
    if bad_timestamps:
        anomalies.append(f"invalid timestamps: {len(bad_timestamps)}")

    print(f"API health: {health}; current-window screenings checked: {len(items)}")
    if anomalies:
        print("Severity: medium")
        print(
            "User impact: some current-window screenings may be duplicated or unusable."
        )
        print("Evidence: " + "; ".join(anomalies) + ".")
        print(
            "Likely cause: source or persistence identity/normalization requires "
            "investigation; this is not confirmed by this bounded check."
        )
        print(
            "Recommended action: compare affected records with the source-specific "
            "importer and existing GitHub issues."
        )
    else:
        print("Severity: low")
        print("User impact: no anomaly detected by the bounded automated checks.")
        print(
            "Evidence: no duplicate IDs or natural keys, required fields are "
            "populated, "
            "timestamps parse, and ticket URLs have valid hosts."
        )
        print(
            "Recommended action: continue monitoring; this check does not validate "
            "every "
            "source field or historical retention policy."
        )
    print("Verification status: completed-data-review")
    write_trace(run, "completed-data-review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
