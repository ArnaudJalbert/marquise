---
type: process
status: active
owner: Aster
review_date: 2026-09-30
---

# Specialist Bot Creation and Maintenance

This process sits within the [[../30-operations/Operating Model]] and uses [[../50-processes/Knowledge Management Protocol]] for its source-of-truth rules. [[../40-agents/Mara — Showtime Data Reliability Specialist]] is the current reference implementation.

## Purpose

This is Aster’s standard operating procedure for creating and maintaining Marquise specialist Bots. It prevents repeated research, keeps Bot roles narrow, and keeps the live Hermes profile aligned with Marquise Atlas.

A Bot is a Hermes profile with its own configuration, credentials, memory, skills, chat history, and identity. Atlas documents the role and operating contract; Hermes stores and runs the live profile.

## Source-of-truth boundary

| Concern | Source of truth |
|---|---|
| Mission, responsibilities, boundaries, handoffs, escalation, review criteria | Atlas agent charter |
| Live name, description, model, skills, tools, MCP servers, avatar, and profile settings | Hermes profile / Bot Mode |
| Code, implementation, issues, PRs, CI, deployments | GitHub repository |
| Live conversation and founding context | Bot’s canonical Bot Chat |

Link the sources when useful. Do not duplicate volatile GitHub status in Atlas.

## Gate 0 — Decide whether a persistent Bot is justified

Before creating one, answer:

- What recurring or specialized problem does this Bot solve?
- Why can Aster or a temporary delegated subagent not handle it?
- What distinct output will it produce?
- What tools, permissions, and context are minimally required?
- What measurable improvement would justify keeping it?
- What is the review date or retirement condition?

Prefer direct execution or a temporary delegation when the work is one-off, exploratory, or not yet a recurring bottleneck. Never create a Bot merely to make the roster larger.

## Gate 1 — Write the charter before creation

Create `atlas/40-agents/<Name> — <Role>.md` with:

```markdown
---
type: agent-charter
status: active
name: <Personal name>
pronouns: <pronouns>
role: <stable-role-slug>
reports_to: Aster
profile: <hermes-profile-slug>
---

# <Name> — <Role>

## Mission
<One clear mission tied to Marquise value, trust, learning, retention, or growth.>

## Responsibilities
- <Owned responsibility>

## Standard output
<Required report or artifact format.>

## Boundaries
- <What the Bot must not decide or change>

## Collaboration
- <Who it reports to>
- <Approved handoffs and direct Bot communication>
- <Escalation conditions>

## Review
<Review date, success measures, and retirement criteria.>
```

Use a personal name and pronouns for every Bot. Keep the functional role explicit in the title and charter.

## Gate 2 — Create the Hermes profile

### Preferred: Hermes Desktop Bot Mode

1. Open the **Bots** tab.
2. Choose **New Agent**.
3. Set the personal name, functional title, and concise description.
4. Use **Fresh profile** or **Create empty** unless cloning is deliberately justified.
5. Set the custom `SOUL.md` from the approved charter.
6. Pin a model only when the role needs a different model; otherwise inherit the launch profile.
7. Enable only the skills, toolsets, and MCP servers the role needs.
8. Keep shared credentials enabled where appropriate; do not distribute secrets in chat or Atlas.
9. Choose the intended connection/backend if multiple machines are configured.
10. Create the profile and confirm it appears in the roster.

### CLI fallback

Use Hermes’ profile commands when Desktop is unavailable. Resolve paths through the active Hermes home; do not hardcode `~/.hermes`.

```bash
hermes profile list
hermes profile create <profile-slug> --no-skills \
  --description "<one- or two-sentence routing description>"
hermes profile describe <profile-slug> --text "<exact description>"
hermes profile show <profile-slug>
```

Profile slugs are lowercase, alphanumeric names suitable for a directory. The personal display name belongs in the profile identity and `SOUL.md`; the slug is an implementation identifier.

If the profile needs inherited provider configuration, use the supported clone/configuration path rather than hand-editing Hermes configuration. A clone may copy more skills than intended, so inspect and narrow capabilities afterward. Never put credentials in Atlas, source control, or a Bot prompt.

### GitHub access prerequisite

When a Bot must inspect private repositories, issues, pull requests, GitHub Actions, or repository code:

1. Enable only the required GitHub skills and tool access, such as `github-auth`, `github-repo-management`, `github-issues`, or `github-code-review`.
2. Reuse an existing approved GitHub credential through the supported profile/environment credential mechanism when appropriate; do not create or rotate a token unnecessarily.
3. Ensure the credential is available inside the Bot’s isolated runtime, not only in Aster’s shell, host-level Git configuration, or another profile.
4. Verify authenticated access from the Bot itself against the exact private repository and required endpoint (for example, repository contents and Actions run metadata).
5. If access is unavailable or insufficient, mark the Bot or dependent routine as blocked rather than treating a `404`, unauthenticated response, or local workflow file as proof of access.

Use the minimum permissions required. Keep tokens in credential storage or the profile’s secret environment only; never record token values in Atlas, chat, prompts, logs, or Git diffs.

### GitHub operating procedure for Bots

When GitHub is part of an assigned task, the Bot must use the GitHub CLI (`gh`) as the standard interface. Do not substitute browser scraping, guessed URLs, or unauthenticated local files for GitHub access.

Before inspecting or changing anything:

```bash
gh --version
gh auth status
```

If `gh` is unavailable or unauthenticated, stop and report the access blocker. Do not claim that a repository, issue, pull request, workflow, or fix was inspected.

For a Marquise task, verify the exact repository first:

```bash
gh repo view ArnaudJalbert/marquise
gh run list --repo ArnaudJalbert/marquise --limit 10
```

Use `--repo ArnaudJalbert/marquise` explicitly whenever the working directory is not already the Marquise repository. Typical read operations include:

```bash
gh issue list --repo ArnaudJalbert/marquise
gh pr list --repo ArnaudJalbert/marquise
gh pr view <number> --repo ArnaudJalbert/marquise
gh run view <run-id> --repo ArnaudJalbert/marquise
gh run view <run-id> --repo ArnaudJalbert/marquise --log-failed
gh api repos/ArnaudJalbert/marquise/contents/<path>
```

For changes, follow the repository’s contribution and PR rules. Prefer a branch and pull request; do not push directly to the default branch unless that authority has been explicitly granted. After any GitHub write, read the exact target back with `gh` and report the resulting URL or identifier. A successful CLI command alone is not proof that the requested change is complete.

### Atlas awareness for Bots

Before work that affects Marquise strategy, product context, operating procedures, agent responsibilities, or data-reliability workflows, the Bot must read the relevant Marquise Atlas notes. At minimum, Mara reads:

- `atlas/README.md`
- `atlas/50-processes/Knowledge Management Protocol.md`
- `atlas/50-processes/Specialist Bot Creation and Maintenance.md`
- `atlas/40-agents/Mara — Showtime Data Reliability Specialist.md`

Atlas is the source of truth for Mara’s mission, boundaries, handoffs, and operating procedures. GitHub remains the source of truth for code, issues, PRs, CI, releases, deployments, and implementation history. Mara must link these sources rather than copying volatile GitHub status into Atlas.

## Gate 3 — Install the role identity

Write the approved role into the Bot’s `SOUL.md`. It must include:

- Personal name and pronouns
- Mission
- Responsibilities and non-goals
- Standard output contract
- Decision rights and boundaries
- Collaboration partners and handoff protocol
- Escalation conditions
- Quality/completion criteria
- Review and retirement criteria

The SOUL is the live standing instruction. The Atlas charter is the durable company record. Keep them materially aligned; Atlas may be more concise, but it must not contradict the live profile.

## Gate 4 — Give the Bot founding context

Open the Bot’s canonical Bot Chat and provide:

- The role and mission
- The current Marquise context relevant to the role
- Reporting relationship to Aster
- Boundaries and approval requirements
- Expected first response or output format

For CLI verification:

```bash
hermes -p <profile-slug> chat -q \
  "You are <Name>, <pronouns>, Marquise’s <role>. Read SOUL.md. Confirm your mission, responsibilities, boundaries, and output format."
```

The founding exchange is successful only when the Bot responds in role. A profile existing on disk is not proof that the Bot is usable.

## Gate 5 — Verify before reporting completion

Run and record evidence for all applicable checks:

- `hermes profile show <profile-slug>` confirms the profile path, model, gateway state, skills, `.env`, and `SOUL.md`.
- The SOUL contains the approved name, pronouns, mission, boundaries, and output contract.
- The Bot responds to a founding-context message in its canonical chat.
- The Atlas charter exists under `atlas/40-agents/`.
- The profile has only the intended capabilities and no unnecessary permissions.
- For any required private GitHub access, the Bot independently authenticates and can read the exact repository and Actions metadata it needs.
- For GitHub-dependent work, the Bot uses `gh`, verifies the exact repository, and reads the relevant Atlas notes before acting.
- Sensitive credentials are not present in the charter, chat seed, or Git diff.

Do not report a Bot as ready based solely on a successful creation command.

## Updating a Bot as the role evolves

When adding responsibilities, tools, or workflows:

1. Identify the change and why it improves a current objective.
2. Check that the change does not overlap another Bot or exceed the role’s mandate.
3. Update the Atlas charter first, including boundaries, outputs, collaborators, and review criteria.
4. Update the live Bot profile through Bot Mode or the supported Hermes command/configuration path.
5. Update `SOUL.md` to match the approved charter.
6. If capabilities change, review skills, toolsets, MCP servers, credentials, and permissions explicitly.
7. Send the Bot a bounded change briefing in canonical Bot Chat and ask it to restate the changed contract.
8. Run a representative task or verification prompt.
9. Record the material decision or learning in `70-decisions-and-reviews/` when it is likely to be revisited.
10. Commit and push Atlas changes through the normal GitHub PR workflow.

Do not silently expand a Bot’s mandate because it performed well on an unrelated task. Split the role, use a temporary subagent, or ask Arno for a product/workflow decision when the change is material.

## Collaboration protocol

Bot-to-Bot communication is allowed only inside an active workflow. Each handoff must state:

- Sender and recipient
- Objective and relevant context
- Exact requested output
- Constraints and authority
- Completion or escalation condition

Bots may not create uncontrolled communication chains, make founder-level decisions, or approve sensitive or irreversible actions.

## Review, simplify, or retire

At each review date, ask:

- What useful work did the Bot complete?
- What measurable signal improved?
- Was its output verified and acted upon?
- Did it reduce founder or Aster attention, or add coordination cost?
- Is its role still distinct?
- Should it be simplified, merged, retrained, paused, or retired?

Retire or hide underused Bots rather than keeping a decorative roster. Preserve consequential charter history in Atlas when the role changes or ends.

## Current example

[[40-agents/Mara — Showtime Data Reliability Specialist]] is the reference implementation. Mara’s role demonstrates the expected pattern: a personal identity, narrow data-reliability mission, evidence-backed output, explicit production boundaries, direct escalation rules, and a review after an initial monitoring pilot.
