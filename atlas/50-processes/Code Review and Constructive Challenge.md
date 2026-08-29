---
type: process
status: pilot
owner: Aster
review_date: 2026-09-30
---

# Code Review and Constructive Challenge

Use [[Documentation and Delivery Workflow]] for the repository PR template, story/brief handoff, and verification gates.

## Rule

No rubber stamps. The author and reviewer challenge the work, not each other. Evidence beats confidence; changing your mind is good work.

## Ponytail

Use Ponytail `full` by default: question the requirement, reuse existing code, prefer standard or native solutions, and write the smallest complete change. Do not add abstractions, dependencies, or flexibility without a concrete payoff.

Ponytail never overrides safety, correctness, data integrity, Clean Architecture, acceptance criteria, or required tests. A shorter diff is not automatically better.

## Roles

- **Author:** defines acceptance criteria, keeps scope focused, states risks and weakest assumption, and answers every substantive comment.
- **Reviewer:** is independent, reads the issue/rules/diff/CI, challenges correctness and complexity, and re-reviews fixes.
- **Aster:** assigns reviewers, classifies risk, resolves routine technical disagreements, and verifies readiness.
- **Arno:** decides product intent, major architecture, irreversible migrations, security posture, material cost, and priority.

The primary reviewer cannot adjudicate their own unresolved finding. Use a fresh reviewer or escalate.

## Workflow

1. **Prepare:** PR body contains the issue or, for trivial docs/metadata, acceptance criteria; focused scope; checks; risks; and migration/rollback notes where relevant.
2. **Review:** use concise comments prefixed `Blocker`, `Challenge`, `Suggestion`, or `Question`. Include evidence, impact, and next action. Check inward dependency direction, layer ownership, injection, DTO/public-facade boundaries, and unjustified abstractions or dependencies. If no material objection exists, state what was tested and the residual risk.
3. **Resolve:** fix valid findings and reply with commit plus verification. For disagreement, provide evidence. If uncertain, run one smallest time-boxed experiment.
4. **Close:** every substantive comment gets one disposition: `fixed`, `withdrawn`, `accepted-risk`, `escalated-and-decided`, or `non-blocking follow-up`. Questions and suggestions do not require code when their rationale is recorded.
5. **Re-review:** inspect the changed diff, not just replies. A substantive push requires re-review of its changed range.

## Ready to merge

All acceptance criteria and required checks pass on the current head; no blocker or consequential challenge remains; migrations have compatibility/rollback evidence; and an independent reviewer approved that exact SHA.

During the pilot, the reviewer records the approved SHA and Aster compares it with the merge head. Readiness is not authorization:

| Action | Authority |
|---|---|
| Review approval | Independent reviewer |
| Routine merge/deploy | Arno or a human explicitly delegated by Arno |
| High-risk merge/deploy | Arno |
| Bot merge/deploy | Requires Arno's explicit per-action authorization |

## Afterward

Verify production, data, or operational effects after merge/deploy. Record recurring lessons in the repository or Atlas.

## Reject

Self-review, opinion-only debate, scope creep, manufactured objections, optional-comment rewrites, merging on green CI alone, or unresolved threads hidden by a small diff.

## Pilot

Run manually until 2026-09-30. Measure defect detection, decision clarity, review time, and founder attention before adding automation or a dedicated review Bot.
