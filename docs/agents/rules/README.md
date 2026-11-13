# Marquise rules

Repository rules for agents and humans. The index, with when to read each file, is in [AGENTS.md](../../../AGENTS.md#rules).

## Where knowledge goes

| Knowledge | Home |
|---|---|
| A rule that holds in any of Arnaud's repos | A Calepin coding standard ([AGENTS.md](../../../AGENTS.md#shared-coding-standards)) |
| A rule only Marquise follows, or how Marquise applies a shared one | A topic file here |
| A domain term | The relevant `CONTEXT.md` ([docs/agents/domain.md](../domain.md)) |
| A hard-to-reverse decision and its reason | An ADR under `docs/adr/` |
| How to run, set up or operate something | `CONTRIBUTING.md` or a `docs/` guide |

## Rule format

- Each topic file opens with a `Read when ...` line naming the work that needs it.
- One rule per bullet, stated as the behaviour to follow. Add the reason when it is not obvious.
- A rule a test or script checks ends with `**Enforced:** <path>`. Untagged rules are checked in review.
- Each rule has one home. Other docs link to it.

## Adding or changing a rule

1. Put a portable rule in Calepin's coding standards, not here. Put a Marquise rule in the topic file whose `Read when` line matches. Create a new file only for a new kind of work, and add its row to the AGENTS.md index in the same PR.
2. When a rule and the code disagree, change one of them in the same PR, or file an issue that names both.
3. When review catches the same violation twice, promote the rule to a check: an architecture test in `packages/marquise-core/tests/unit_tests/` or a build script under `web/`. Then add the `**Enforced:**` tag.
4. Delete rules that no longer bear on the code. Git keeps the history.
