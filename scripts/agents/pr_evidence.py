#!/usr/bin/env python3
"""Check the parts of a PR's delivery evidence a script can prove, read-only.

The loop's review run calls this instead of asking an agent whether CI passed,
tests changed and the template is filled. Prints JSON; exits 0 when every check
passes, 1 when one fails and 2 when GitHub cannot be read.

    uv run --no-project --python 3.13 scripts/agents/pr_evidence.py \\
        --repo ArnaudJalbert/marquise --pr 605
"""

import argparse
import json
import re
import subprocess
import sys

FIELDS = "headRefOid,mergeable,additions,deletions,body,files,statusCheckRollup"
SECTIONS = ("Summary", "Verification", "Outcome", "Linked issue")
PLACEHOLDERS = (
    "Describe each change in an imperative sentence.",
    "List each check and its result.",
    "<!-- State the result and any remaining risk. -->",
    "Closes #123",
)
GREEN = {"SUCCESS", "SKIPPED", "NEUTRAL"}
MAX_CHANGED_LINES = 3000
TEST_PATH = re.compile(r"(^|/)tests?/|(^|/)test_[^/]*\.py$|\.(test|spec)\.tsx?$")
CODE_PATH = re.compile(r"\.(py|tsx?|jsx?)$")


def check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "pass": passed, "detail": detail}


def ci_green(rollup: list[dict]) -> dict:
    """Every reported check finished green and at least one succeeded."""
    states = [
        item.get("conclusion") or item.get("state") or item.get("status")
        for item in rollup
    ]
    passed = "SUCCESS" in states and all(state in GREEN for state in states)
    names = ", ".join(
        f"{item.get('name') or item.get('context')}={state}"
        for item, state in zip(rollup, states)
    )
    return check("ci_green", passed, names or "no checks reported on this head")


def tests_changed(paths: list[str], body: str) -> dict:
    """Code changes come with a test change or a `No new test: why` line."""
    code = [
        path for path in paths if CODE_PATH.search(path) and not TEST_PATH.search(path)
    ]
    tests = [path for path in paths if TEST_PATH.search(path)]
    reason = re.search(r"\bno (new )?tests?: *\S", body, re.I)
    passed = not code or bool(tests) or bool(reason)
    return check(
        "tests_changed", passed, f"{len(code)} code files, {len(tests)} test files"
    )


def section_text(body: str, name: str) -> str | None:
    """Return a section's text up to the next heading, or None when it is absent."""
    match = re.search(rf"^#+\s*{name}\s*$(.*?)(?=^#|\Z)", body, re.M | re.I | re.S)
    return match and re.sub(r"<!--.*?-->", "", match.group(1), flags=re.S).strip()


def body_sections(body: str) -> dict:
    """Every template section is present, has content and drops the placeholders."""
    texts = {name: section_text(body, name) for name in SECTIONS}
    missing = [name for name, text in texts.items() if text is None]
    empty = [name for name, text in texts.items() if text == ""]
    left = [text for text in PLACEHOLDERS[:3] if text in body]
    problems = [
        missing and f"missing {missing}",
        empty and f"empty {empty}",
        left and f"placeholder {left}",
    ]
    detail = "; ".join(filter(None, problems))
    return check("body_sections", not detail, detail or "all sections filled")


def closes_issue(body: str) -> dict:
    match = re.search(r"\b(closes|fixes|resolves) #(\d+)", body, re.I)
    passed = bool(match) and match.group(2) != "123"
    return check(
        "closes_issue", passed, match.group(0) if match else "no Closes #N line"
    )


def diff_size(data: dict) -> dict:
    """A conflicting or oversized diff cannot be reviewed until it is rebased."""
    lines = data["additions"] + data["deletions"]
    passed = data["mergeable"] != "CONFLICTING" and lines <= MAX_CHANGED_LINES
    return check("diff_size", passed, f"{lines} changed lines, {data['mergeable']}")


def evaluate(data: dict) -> dict:
    body = data["body"] or ""
    checks = [
        ci_green(data["statusCheckRollup"] or []),
        tests_changed([file["path"] for file in data["files"]], body),
        body_sections(body),
        closes_issue(body),
        diff_size(data),
    ]
    return {
        "head": data["headRefOid"],
        "checks": checks,
        "pass": all(c["pass"] for c in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, help="OWNER/REPO")
    parser.add_argument("--pr", required=True, type=int)
    args = parser.parse_args()
    try:
        output = subprocess.run(
            ["gh", "pr", "view", str(args.pr), "--repo", args.repo, "--json", FIELDS],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout
        result = {"pr": args.pr, **evaluate(json.loads(output))}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
        print(f"PR evidence unreadable; no result: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
