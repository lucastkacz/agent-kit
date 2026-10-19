# 1. A plugin agent for the cloud routines, instead of a fork of the control tower

- **Status:** accepted
- **Date:** 2026-10-19
- **Issue:** #175 (spike)

## Context

The batch skills reach Anthropic's cloud routines only through the `RemoteTrigger` tool. A general-purpose subagent can't load it, so run-batch and accept-batch hand every `RemoteTrigger` job to a fork of the control tower, which copies the whole session. In batch #153, the fork that created six routines used 486k tokens, the one that read five run reports 315k, and the one that read #138's run log at the acceptance 246k, all on the control tower's model.

The question: can a subagent defined by the plugin, an `agents/<name>.md` with `RemoteTrigger` among its `tools`, make those calls, and what does it cost against a fork?

## What the spike tried

A throwaway plugin, loaded with `claude -p --plugin-dir`, held one agent:

```markdown
---
name: routines
description: Reads the account's cloud routines with the RemoteTrigger tool and reports only what it is asked.
tools: RemoteTrigger, Read, Grep
model: haiku
---

You read the account's cloud routines with the `RemoteTrigger` tool. Make only the calls you are asked for, never `create`, `update`, `run` or `delete`, and report only what you are asked, in a few lines.
```

Five `claude -p` sessions (Claude Code 2.1.303, on haiku) asked that agent, through the `Agent` tool, for read-only calls. The session itself never called `RemoteTrigger`.

| Probe | The agent's `tools` | How it ran | Calls | Result | Tokens (cache reads) | Cost |
|---|---|---|---|---|---|---|
| 1 | `RemoteTrigger` | foreground | `list` | called; its 790 KB answer was saved to a file, which the agent had no tool to read | 181k (153k) | $0.0078 |
| 2 | `RemoteTrigger, Read, Grep` | background | `list_runs`, `get_run_log` | no `RemoteTrigger`: the agent had only `Read` and `Grep`, and no `ToolSearch` to load it | 162k (133k) | $0.0076 |
| 3 | `RemoteTrigger, Read, Grep` | foreground | `list_runs`, `get_run_log` | both called (HTTP 200); it read #71's third probe run, one page, 35 events, no `mcp__github__` call | 80k (55k) | $0.0054 |
| 4 | `RemoteTrigger, Read, Grep` | background | `list_runs` | no `RemoteTrigger`, as in probe 2 | 90k (74k) | $0.0041 |
| 5 | `RemoteTrigger, Read, Grep` | foreground | `list` | called; it grepped the saved answer and found 17 routines named `lucastkacz/agent-kit batch …` (6 of #153, 11 of #114) | 80k (60k) | $0.0049 |

The tokens and cost are the whole session's, the agent's and its caller's together, so the agent alone costs less.

## Decision

The batch skills make their `RemoteTrigger` calls through a plugin agent, not through a fork of the control tower:

1. The plugin ships an agent with `tools: RemoteTrigger, Read, Grep` and a small `model`. Its instructions limit it to the calls its caller names, and to reporting only what its caller asks for.
2. The control tower calls it in the foreground, always. In the background, the agent doesn't get `RemoteTrigger`.
3. A large answer, such as `list`'s, is saved to a file. The agent greps that file and never reads it whole.
4. The control tower writes each filled cloud prompt to a file outside the repository, and the agent reads it from there. So the prompt, some 13k characters that each `create` echoes about three times, stays out of both the control tower's context and the agent's report.

## Consequences

- **run-batch, "Send an issue to the cloud":** the agent creates each routine, checks that it holds `mcp__github__*` in its `disallowed_tools`, updates it with `clear_mcp_connections`, and reports its id, branch and firing time. The fork goes.
- **run-batch, "Bring a cloud branch back":** the agent reads the ended runs' reports: their status, the question or what went wrong, the work they found and the environment's problems. The fork goes.
- **run-batch, "Resume":** the agent finds the batch's routines with `list`, grepping the saved answer for the names `<owner/name> batch <batch>: #<n>`.
- **accept-batch, "The cloud runs' denials":** the agent reads each run log, page by page, and reports the denials, the owner's messages and the writes outside the sandbox. The fork goes.
- **Cost:** each job costs about what a fresh small session does, some 80k tokens, mostly the cached system prompt, at the agent's model. A fork costs 246k–486k tokens at the control tower's model.
- **Not tried:** `create` and `update`. Trying them needs a routine that fires, which this spike's issue asked to stop for. They are the same tool, with the same permission as `list` and `get_run_log`. The first batch with a `Cloud:` line tries them, and keeps the fork as the fallback until one has worked.
- **Risk:** the agent acts on the owner's account. Its instructions name the calls it may make, and the control tower names each one. Claude Code's `tools` field limits the agent to its three tools, so it can't run commands or edit files.

## The spike's code

The throwaway plugin lived outside the repository and isn't kept. Its only file of substance is the agent above.
