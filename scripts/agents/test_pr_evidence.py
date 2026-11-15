"""Exercise the PR evidence checks on fixed GitHub data, without the network."""

import pytest
from pr_evidence import evaluate

BODY = """# Summary

- Stop the import at the first failure.

# Verification

- `uv run pytest apps/marquise-cli/tests -q`: 42 passed.

## Outcome

Register stops at the first error. Risk: none known.

## Linked issue

Closes #583
"""


def pr(**changes: object) -> dict:
    """A green PR with a test change and a filled template."""
    return {
        "headRefOid": "abc",
        "mergeable": "MERGEABLE",
        "additions": 40,
        "deletions": 5,
        "body": BODY,
        "files": [
            {"path": "apps/marquise-cli/src/x.py"},
            {"path": "apps/marquise-cli/tests/test_x.py"},
        ],
        "statusCheckRollup": [
            {"name": "Quality", "status": "COMPLETED", "conclusion": "SUCCESS"}
        ],
        **changes,
    }


def failed(data: dict) -> set[str]:
    return {check["name"] for check in evaluate(data)["checks"] if not check["pass"]}


def test_complete_pr_passes() -> None:
    """Green checks, a test change and a filled template need no agent opinion."""
    result = evaluate(pr())
    assert result["pass"] and result["head"] == "abc"


@pytest.mark.parametrize(
    "rollup",
    [
        [],
        [{"name": "Quality", "status": "IN_PROGRESS", "conclusion": None}],
        [{"name": "Quality", "status": "COMPLETED", "conclusion": "FAILURE"}],
    ],
)
def test_missing_pending_or_failed_ci_fails(rollup: list) -> None:
    """Only completed, successful checks on the head count as green."""
    assert failed(pr(statusCheckRollup=rollup)) == {"ci_green"}


def test_skipped_checks_do_not_fail_ci() -> None:
    """A workflow that skipped itself for unrelated paths is not a failure."""
    rollup = [
        {"name": "Quality", "status": "COMPLETED", "conclusion": "SUCCESS"},
        {"name": "Web", "status": "COMPLETED", "conclusion": "SKIPPED"},
    ]
    assert failed(pr(statusCheckRollup=rollup)) == set()


def test_code_without_tests_needs_a_reason() -> None:
    """A code change with no test file passes only if Verification says why."""
    files = [{"path": "apps/marquise-cli/src/x.py"}]
    assert failed(pr(files=files)) == {"tests_changed"}
    reason = BODY.replace("42 passed.", "42 passed. No new test: behaviour unchanged.")
    assert failed(pr(files=files, body=reason)) == set()
    assert failed(pr(files=[{"path": "docs/setup.md"}])) == set()


@pytest.mark.parametrize(
    "old, new, check",
    [
        ("# Verification", "# Checks", "body_sections"),
        (
            "- Stop the import at the first failure.",
            "- Describe each change in an imperative sentence.",
            "body_sections",
        ),
        ("Closes #583", "Closes #123", "closes_issue"),
        ("Closes #583", "Related to #583", "closes_issue"),
    ],
)
def test_template_must_be_filled(old: str, new: str, check: str) -> None:
    """Missing or placeholder sections and a missing Closes line fail."""
    assert check in failed(pr(body=BODY.replace(old, new)))


@pytest.mark.parametrize(
    "changes", [{"mergeable": "CONFLICTING"}, {"additions": 2900, "deletions": 200}]
)
def test_conflicting_or_oversized_diff_fails(changes: dict) -> None:
    """A diff the reviewer cannot read, such as after a force-push, needs a rebase."""
    assert failed(pr(**changes)) == {"diff_size"}
