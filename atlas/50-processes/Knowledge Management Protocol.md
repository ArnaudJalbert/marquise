---
type: process
status: active
owner: Aster
---

# Knowledge Management Protocol

This protocol implements the source-of-truth boundary established by [[../70-decisions-and-reviews/Marquise Atlas as Company Knowledge Base]] and supports the navigation conventions in [[../README]]. The practical execution loop is [[Documentation and Delivery Workflow]].

## Source-of-truth boundaries

- **GitHub Issues**: planning, brainstorming, research, proposals, task context, and implementation records.
- **GitHub PRs**: code review, checks, and delivery history.
- **Marquise Atlas**: broad strategy, principles, operating procedures, agent charters, durable decisions, and validated learning.

## Rules

1. Keep active planning in GitHub Issues; use `type:idea`, `type:research`, or `type:proposal` as appropriate.
2. Link GitHub records; do not manually mirror their live status in Atlas.
3. Record only durable, consequential decisions and validated learning in Atlas.
4. Archive rather than delete superseded organizational knowledge when history matters.
5. Keep sensitive material out of broadly accessible notes and repositories.

## Atlas change authority and workflow

- **Anyone (Arno or any Bot) may open a pull request that modifies Atlas.** Specialist Bots may draft and submit Atlas changes through PRs.
- **Only Aster or Arno may merge Atlas pull requests.** Aster is responsible for checking that a proposed change is accurate, scoped, and consistent with existing Atlas notes before merging.
- Arno retains final authority over strategy, priorities, and consequential decisions.
- Every Atlas change must be isolated on a branch, committed with a focused message, pushed, and submitted as a pull request targeting `main`. Do not modify `main` directly.
- Before opening the pull request, the author reviews the complete diff, preserves unrelated work, and runs applicable checks. After opening it, they report its exact URL, changed files, and verification state.
- Atlas is not considered updated until the pull request is reviewed and merged by Aster or Arno. The pull request is the authoritative delivery path for the change; chat is coordination only.
