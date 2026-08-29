---
type: process
status: pilot
owner: Aster
review_date: 2026-09-30
---

# Code Review and Constructive Challenge

## Purpose

Make every code change more correct and more defensible without turning review into ceremony. The author and reviewer are jointly responsible for the outcome; neither role exists to protect its own work.

## Philosophy

- **No rubber stamps.** Approval means the reviewer would be comfortable owning the change.
- **Challenge the work, not the person.** Direct disagreement is expected; defensiveness and performative politeness are not useful.
- **Lead with the strongest objection, if one exists.** If no material objection remains, state what was tested or attempted to falsify and the principal residual risk.
- **Evidence beats authority.** Prefer a test, trace, benchmark, query plan, reproduction, or repository rule over opinion.
- **Changing your mind is good work.** Authors fix valid findings immediately; reviewers withdraw findings disproved by evidence.
- **Keep scope honest.** Review the approved issue and the bug class it represents, not unrelated cleanup.

## Roles

### Author

- Links the issue and acceptance criteria.
- Self-reviews the complete diff before requesting review.
- Reports exact checks, risks, exclusions, and known uncertainty.
- States the change's weakest assumption and what evidence would disprove it.
- Responds to every review thread with a fix, evidence-backed disagreement, or escalation.

### Independent reviewer

- Must not be the author or the same agent context that implemented the change.
- Reviews from the issue, repository rules, and diff—not from the author's confidence.
- Checks correctness, architecture, tests, security, data integrity, performance, and operability where relevant.
- Verifies fixes and resolves threads; the author does not approve their own answer.
- The primary reviewer never adjudicates their own unresolved finding. Assign a fresh adjudicator or escalate to the appropriate decision owner.

Use a specialist Bot when the change is inside its charter. Otherwise use Aster or a temporary reviewer with fresh context. Do not create a permanent review Bot until repeated workload proves the need.

### Aster

- Assigns the reviewer and prevents self-review.
- Ensures the highest-risk area receives the right specialist.
- Reconciles technical disagreements when evidence is sufficient.
- Verifies thread closure, current-head CI, and the final artifact before reporting readiness.

### Arno

Decides disagreements involving product intent, major architectural direction, irreversible migrations, security posture, cost, or priority. Routine implementation disagreements should not be escalated to him before an evidence-based attempt to resolve them.

Aster classifies the risk and disagreement category by default, subject to Arno's override. Treat product intent, major architecture, irreversible migrations, security posture, material cost, and production-impacting operations as consequential/high-risk; treat isolated implementation choices as routine unless their evidence shows otherwise.

### 1. Make the PR reviewable

For non-trivial changes, the author provides:

- linked issue and finite acceptance criteria;
- focused diff with no unrelated changes;
- exact local checks and results;
- migration, rollout, rollback, and compatibility notes where applicable;
- explicit risks, exclusions, and weakest assumption.

For trivial documentation or metadata changes, the PR body may serve as the issue and acceptance record. Use `N/A` for inapplicable checks with a reason, and include a short risk statement. Independent review still applies.

Draft PRs may receive early design feedback, but they are not eligible for approval.

### 2. Assign an independent reviewer

Aster assigns one primary reviewer. Add another only when the change crosses a meaningful specialty boundary, such as data migration plus frontend behavior. More reviewers are not automatically better.

The reviewer reads the issue, full thread, repository rules, relevant history, complete diff, and current CI state before commenting.

### 3. Review with explicit comment types

Prefix substantive comments:

- **Blocker:** correctness, security, data loss, broken architecture, failed acceptance criterion, or unverified high-risk behavior.
- **Challenge:** a material assumption or design choice that needs evidence or a stronger alternative.
- **Suggestion:** worthwhile but non-blocking improvement.
- **Question:** missing context; not implicitly a blocker.

A useful comment includes the evidence, impact, and recommended next action. Style preferences are not blockers unless they violate an enforced standard.

### 4. Resolve through evidence

For each comment, record one terminal disposition: `fixed`, `withdrawn`, `accepted-risk`, `escalated-and-decided`, or `non-blocking follow-up`.

1. **Agree:** the author fixes it, adds or updates proof, pushes, and replies with the commit and verification.
2. **Disagree:** the author explains why with code, tests, measurements, history, or documented constraints.
3. **Still uncertain:** author and reviewer define one smallest experiment that could settle it, with an explicit timebox.
4. **Still consequential:** Aster decides routine technical execution; Arno decides founder-level trade-offs.

Questions and suggestions may close as `withdrawn` or `non-blocking follow-up` without implementation when the author and reviewer state why. After one agreed experiment or its timebox expires, the named decision owner decides and records the rationale. The reviewer should explicitly acknowledge when the author's evidence changes their view. Do not prolong a settled point to preserve status.

### 5. Re-review the actual result

After changes, the reviewer:

- reads the new diff rather than only the replies;
- checks that fixes did not create new scope or regressions;
- confirms every blocker is resolved or explicitly escalated;
- verifies current-head CI and required local/integration evidence;
- approves only the exact reviewed head.

A new substantive push after approval requires re-review of the changed range.

### 6. Readiness gate

A PR is ready to merge only when:

- acceptance criteria are met;
- required checks are green on the current head;
- no blocker or unresolved consequential challenge remains;
- migrations have a tested compatibility and rollback plan;
- the independent reviewer has approved the exact current head;
- required Arno approval has been obtained for high-risk decisions.

During the pilot, the reviewer records the approved commit SHA in the PR. Aster compares it with the merge head before reporting readiness. A substantive push invalidates the approval for the changed range.

Readiness is a recommendation, not merge or deployment authorization. Authority is explicit:

| Action | Routine authority | Always requires Arno |
|---|---|---|
| Approve review | Independent reviewer | No, unless the change contains a founder-level decision |
| Merge | Arno, or a human explicitly delegated by Arno | Security posture, irreversible migration, material cost, or other high-risk change |
| Deploy | Arno, or a human explicitly delegated by Arno | Production-impacting or irreversible deployment |
| Bot merge/deploy | Not authorized by this process | Requires explicit per-action authorization from Arno |

The author may not approve their own change. The reviewer may merge only when Arno has explicitly delegated that authority for the change; review approval alone is never merge authorization.

### 7. Close the loop

For changes with production, data, or operational effects, verify behavior after merge/deployment and record material learnings. If the review exposed a recurring failure pattern, update the appropriate repository rule, test, or process instead of relying on memory.

## Anti-patterns

- Author reviewing their own implementation through a second prompt with shared assumptions.
- Reviewer agreeing because CI is green.
- Author applying every suggestion without evaluating it.
- Reviewer rewriting the solution through many optional comments.
- Opinion-only disagreement when a small test could decide it.
- Escalating routine technical debate to Arno before trying evidence.
- Merging with unresolved threads because the change appears small.

## Pilot review

Run this process manually first. At the review date, assess whether it improved defect detection, decision clarity, review time, and founder attention. Automate assignment or add a dedicated reviewer Bot only if repeated evidence justifies it.
