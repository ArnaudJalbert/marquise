---
type: process
status: active
owner: Aster
---

# Knowledge Management Protocol

This protocol implements the source-of-truth boundary established by [[../70-decisions-and-reviews/Marquise Atlas as Company Knowledge Base]] and supports the navigation conventions in [[../README]]. The practical execution loop is [[Documentation and Delivery Workflow]].

## Source-of-truth boundaries

- **GitHub (`ArnaudJalbert/marquise`)**: code, issues, PRs, CI, releases, deployments, and implementation-level records.
- **Marquise Atlas**: strategic context, operating procedures, decision records, research, agent charters, and project briefs.
- **Personal vault**: private founder thinking and personal notes.

## Rules

1. Link GitHub records; do not manually mirror their live status in Atlas.
2. Record decisions that are durable, consequential, or likely to be revisited.
3. Give active notes a status and owner where useful.
4. Archive rather than delete superseded organizational knowledge when history matters.
5. Keep sensitive material out of broadly accessible notes and repositories.

## Atlas change authority and workflow

- **Aster is the only agent authorized to create, edit, move, archive, or delete Atlas notes.** Specialist Bots may propose documentation changes or supply draft content, but they must not modify Atlas directly.
- Arno retains final authority over strategy, priorities, and consequential decisions. Aster may apply approved documentation changes and is responsible for checking that they are accurate, scoped, and consistent with existing Atlas notes.
- Every Atlas change made by Aster must be isolated on a branch, committed with a focused message, pushed, and submitted as a pull request targeting `main`. Aster must not modify `main` directly.
- Before opening the pull request, Aster reviews the complete diff, preserves unrelated work, and runs applicable checks. After opening it, Aster reads the pull request back and reports its exact URL, changed files, and verification state.
- Atlas is not considered updated until the pull request is reviewed and merged. The pull request is the authoritative delivery path for the change; chat is coordination only.
