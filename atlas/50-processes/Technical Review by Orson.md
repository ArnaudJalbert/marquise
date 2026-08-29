---
type: process
status: active
owner: Orson
review_date: 2026-09-30
---

# Technical Review by Orson

This is the review gate described in [[../40-agents/Orson — Staff Engineer and Architecture Lead]] and a technical implementation of the [[../30-operations/Operating Model]] execution standard.

## Purpose

Ensure every Marquise PR receives one independent, evidence-based technical review before Arno’s final review or merge decision.

## Trigger

A non-draft PR is ready when its author has stated the intended outcome, scope, tests, and known risks. Material pushes after a verdict require re-review of the latest head commit.

## Procedure

1. **Understand:** read the PR description, linked issue/decision record, changed-file list, and current CI status.
2. **Inspect:** read the full diff and enough surrounding code to assess behavior and ownership boundaries.
3. **Validate:** run proportionate local checks when needed; verify live CI rather than inferring it from local commands.
4. **Challenge:** check correctness, edge cases, architecture/dependency direction, data integrity, security/privacy, performance, test coverage, migration/rollback risk, and scope.
5. **Respond:** submit one verdict—**approve**, **changes requested**, or **comment**—with file/line evidence for material findings. Separate merge blockers from suggestions.
6. **Re-review:** after material changes, verify the new head commit and updated CI before approval.
7. **Handoff:** summarize the verdict, evidence, test/CI state, and remaining risk for Arno through Aster.

## Rules

- Orson does not approve his own PRs; another independent reviewer is required.
- An approval is not merge or deployment authority.
- Small, self-contained PRs with related tests are the default. If a larger change is unavoidable, agree on the design and review plan before implementation.
- Do not block on taste, speculative abstractions, or non-material style preferences.
- Do not approve based only on a passing command, a prior revision, or an agent claim.

## Escalate

Escalate to Arno through Aster when a decision changes product scope, introduces a material external cost, creates an irreversible commitment, materially changes the technical stack, or leaves a consequential technical dispute unresolved.

## Completion record

Each review must leave a GitHub review/comment and a concise Aster handoff containing the PR link, latest commit reviewed, verdict, blockers, tests/CI, and unresolved risk.
