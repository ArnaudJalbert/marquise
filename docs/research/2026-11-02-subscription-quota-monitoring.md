---
type: research
status: complete
date: 2026-11-02
---

# Subscription quota monitoring for the VPS agent loop

## Scope and recommendation

Find a deterministic, unattended way to read remaining account allowance for Codex, Claude and OpenCode Go on the Debian VPS. Research covers upstream documentation and source; it does not validate live credentials or install a collector.

Recommendation: evaluate a pinned CodexBar Linux CLI first. It offers one JSON interface across the required providers. Prefer Codex's native CLI source, require measured API data for Go, and validate Claude account-usage permissions before connecting a gate. Keep the collector behind the loop's small preflight interface. This is an engineering recommendation, not a verified deployment. [CodexBar CLI](https://github.com/steipete/CodexBar/blob/v0.83.0/docs/cli.md), [Linux release assets](https://github.com/steipete/CodexBar/releases/tag/v0.83.0).

## Existing gap

The installed loop preflight always returns `usage_meter: unknown`. It implements safe failure behavior, not a connection to a meter. The inspected T3 MCP catalog and VPS CLI help expose no quota read. These are local observations from this investigation, not claims about every T3 release.

T3 already collects subscription windows in Usage → Limits. `/usage-limits` displays that snapshot in the UI without starting the agent or refreshing data. Automatic checks are client-triggered and spaced at least five minutes apart. A UI snapshot is therefore not an unattended sampling contract. Adding a usage hub supplies more accounts to the UI but does not itself expose an agent tool. [T3 0.1.6 usage documentation](https://github.com/pingdotgg/t3code/blob/v0.1.6/docs/user/usage.md).

## Options

| Option | What it provides | Main tradeoff | Fit |
| --- | --- | --- | --- |
| Expose T3's existing limits through a read-only MCP tool | Reuses its account/provider integration | Requires a T3 change with freshness and error semantics | Clean long-term integration |
| CodexBar CLI | Linux JSON allowance reads for the required providers | Third-party dependency and provider-specific authentication | Best first experiment |
| Native provider adapters | Codex app-server and Claude SDK reports | We maintain multiple protocols and version compatibility | Targeted fallback |
| ccusage | Local tokens, costs and reconstructed activity blocks | Does not establish account subscription headroom | Accounting only |

The T3 extension is a proposed implementation, not an existing exposed tool. The other capabilities are documented by their upstream projects. [CodexBar CLI](https://github.com/steipete/CodexBar/blob/v0.83.0/docs/cli.md), [Codex app-server](https://learn.chatgpt.com/docs/app-server), [Claude SDK reference](https://code.claude.com/docs/en/agent-sdk/typescript#sdkusagereport), [ccusage](https://github.com/ccusage/ccusage/blob/main/apps/ccusage/README.md).

### CodexBar

Release 0.83.0 ships standalone Linux CLI archives for x86_64 and ARM64, including musl builds. Its remote usage output includes percentages, reset times and an update timestamp. It can run without the desktop application. This is an independent project, not an OpenAI or Anthropic product. [Release](https://github.com/steipete/CodexBar/releases/tag/v0.83.0), [CLI JSON contract](https://github.com/steipete/CodexBar/blob/v0.83.0/docs/cli.md).

Documented candidate reads:

```sh
codexbar usage --provider codex --source cli --format json --pretty
codexbar usage --provider claude --source oauth --format json --pretty
codexbar usage --provider opencodego --source api --format json --pretty
```

These are proposed validation commands, not commands executed in this research. Let the collector reuse the intended user's native login. Do not copy tokens into command arguments or agent reports. Claude Linux OAuth needs profile access; a token that authenticates model requests can still be insufficient. Go auto mode may produce estimated local-cost data, so require explicit API mode and reject `dataConfidence=estimated`. [Claude authentication](https://github.com/steipete/CodexBar/blob/v0.83.0/docs/claude.md), [Go confidence and sources](https://github.com/steipete/CodexBar/blob/v0.83.0/docs/opencodego.md).

Its built-in guard is not our complete policy. The inspected implementation supports session/weekly selection and an inclusive minimum threshold. Our policy also needs monthly and model-specific windows, account matching, freshness and rejection of estimates. Parse measured JSON through our own small gate. [Guard implementation](https://github.com/steipete/CodexBar/blob/v0.83.0/Sources/CodexBarCLI/CLIGuardCommand.swift).

### Native provider interfaces

Codex documents `account/rateLimits/read` after the app-server initialization handshake. It requires no model turn and returns account windows, supplied durations/reset times, and limit IDs. Use existing CLI-managed subscription authentication. API-key authentication is a separate billing path. Do not assume primary always means five hours or secondary always means weekly. [App-server](https://learn.chatgpt.com/docs/app-server), [Account processor](https://github.com/openai/codex/blob/main/codex-rs/app-server/src/request_processors/account_processor.rs).

Claude's SDK exposes structured `/usage` reports and an explicitly experimental `get_usage` control method. Account plan limits are separate from session cost estimates. Profile scope, installed SDK/CLI compatibility and cache freshness need validation. Rate-limit events help during a run but do not guarantee a complete pre-dispatch snapshot. [SDK usage reports and events](https://code.claude.com/docs/en/agent-sdk/typescript#sdkusagereport), [SDK changelog](https://github.com/anthropics/claude-agent-sdk-typescript/blob/main/CHANGELOG.md).

OpenCode Go's released source implements `/zen/go/v1/usage` with rolling, weekly and monthly server counters. Its newer V2 server offers an experimental usage-limits endpoint. These versions and authentication paths must not be conflated. A custom direct collector would own compatibility and credential handling. [v1.19.5 implementation](https://github.com/anomalyco/opencode/blob/v1.19.5/packages/console/app/src/routes/zen/go/v1/usage.ts), [V2 API](https://opencode.ai/v2/docs/api#usage).

### Accounting and hubs

ccusage reconstructs local token/cost history and activity blocks. It cannot prove how much account-wide subscription allowance remains. Likewise, API organization billing reports and estimated token costs cannot enforce a subscription reserve. [ccusage JSON reports](https://github.com/ccusage/ccusage/blob/main/docs/guide/json-output.md), [Claude usage/cost API](https://platform.claude.com/docs/en/manage-claude/usage-cost-api).

## Proposed validation and gate

1. Verify the pinned collector's Linux compatibility and provenance, without replacing provider CLIs.
2. Run one credential-safe read per required provider. Confirm account identity, measured windows, reset timestamps and source. Compare with T3's refreshed VPS-filtered Limits view.
3. Test expired/missing credentials, unavailable data, stale snapshots and estimated readings. All must yield unknown, not permission to claim work.
4. Adopt a documented freshness limit. A proposed starting value is five minutes, with a refresh before a claim or expensive phase; this is our policy choice, not a provider SLA.
5. Require more than 20% remaining in every applicable window for the chosen provider/model. Include concurrent workers and shared accounts. Luna and Sol can consume the same Codex allowance.
6. Checkpoint issues/PRs before spending the reserve. Use measurements for dispatch decisions, not a promise that any ticket can finish within the reserve.

These steps are proposed acceptance criteria. No researched interface establishes reserved capacity against concurrent account use, and no source guarantees that 20% is enough for an arbitrary ticket. Nightly pickup remains blocked without measured data or an explicitly authorized bounded budget until the experiment succeeds.
