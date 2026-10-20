# 1. A plugin agent for the cloud routines, instead of a fork of the control tower

- **Status:** accepted on 2026-10-20, with the agent run as a headless session (see "In an interactive session")
- **Date:** 2026-10-19
- **Issue:** #175 (spike), then #213 and #235

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
2. The control tower calls it in the foreground, always. In the background, the agent doesn't get `RemoteTrigger`. Since #235, that foreground is a headless session that runs as the agent (see "In an interactive session").
3. A large answer, such as `list`'s, is saved to a file. The agent greps that file and never reads it whole.
4. The control tower writes each filled cloud prompt to a file outside the repository, and the agent reads it from there. So the prompt, some 13k characters that each `create` echoes about three times, stays out of both the control tower's context and the agent's report.

## Consequences

- **run-batch, "Send an issue to the cloud":** the agent creates each routine, checks that it holds `mcp__github__*` in its `disallowed_tools`, updates it with `clear_mcp_connections`, and reports its id, branch and firing time. The fork goes.
- **run-batch, "Bring a cloud branch back":** the agent reads the ended runs' reports: their status, the question or what went wrong, the work they found and the environment's problems. The fork goes.
- **run-batch, "Resume":** the agent finds the batch's routines with `list`, grepping the saved answer for the names `<owner/name> batch <batch>: #<n>`.
- **accept-batch, "The cloud runs' denials":** the agent reads each run log, page by page, and reports the denials, the owner's messages and the writes outside the sandbox. The fork goes.
- **Cost, measured:** a session that makes one or two read-only calls (`list`, `list_runs`, one page of `get_run_log`) through the agent costs some 80k tokens on haiku, mostly the cached system prompt. The forks it would replace cost 246k–486k tokens at the control tower's model, but for bigger jobs, so the two numbers aren't the same job.
- **Cost, not measured:** several `create`s in one session, where each echoes its ~13k-character prompt about three times into the agent's context, some 10k tokens a call, which the agent then reads again on each turn; and reading a log of several pages. One `create` is measured in "In an interactive session". The first batch with a `Cloud:` line measures both.
- **Not tried in the spike:** `create` and `update`. Trying them needs a routine that fires, which this spike's issue asked to stop for. They are the same tool, with the same permission as `list` and `get_run_log`. #235 tried them on a disabled routine (below), and the fork fallback went.
- **Risk:** the agent acts on the owner's account. Its instructions name the calls it may make, and the control tower names each one. Claude Code's `tools` field limits the agent to its three tools, so it can't run commands or edit files.

## In an interactive session

#213 moved the skills to the agent, started with the `Agent` tool in the foreground. Its human check, on 2026-10-20 in the owner's interactive session on Claude Code 2.1.304, failed: the `Agent` tool started `agent-kit:routines` in the background, though the call asked for nothing of the kind, and the tool there has no option to run a subagent in the foreground. The agent's first call, `list`, failed with "No such tool available: RemoteTrigger", and it created nothing. The spike's probes had run in `claude -p`, where the `Agent` tool waited for the agent.

Claude Code's docs name no frontmatter field that keeps a subagent in the foreground: only `background: true`. They name `CLAUDE_CODE_FORK_SUBAGENT=0`, which lets Claude wait for its subagents, and `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, which turns background tasks off everywhere. Both change every subagent of the owner's sessions, so neither was tried.

What works needs no setting: a headless session started from the `Bash` tool that runs as the agent itself, `claude -p --agent agent-kit:routines --allowedTools "RemoteTrigger,Read,Grep" < <a file with the calls, and what to report>`, from the project's main folder, where the plugin is enabled. From another folder, `--agent agent-kit:routines` isn't found when the plugin is enabled at project scope. The session has the agent's three tools and its model, and prints only its report. Two probes, on 2.1.304 and haiku:

| Probe | Calls | Result | Tokens (cache reads) | Cost |
|---|---|---|---|---|
| 1 | `list` | called; it grepped the saved answer and found 17 routines named `lucastkacz/agent-kit batch …` | 113k (94k) | $0.0060 |
| 2 | `list`, `create`, `update` with `clear_mcp_connections: true`, `update` with `enabled: false`, `get` | all called; it created a disabled test routine shaped like a batch's, with a 14k-character prompt read from a file. `create`'s answer listed four MCP connections; after the `update`, none was left, and `disallowed_tools` held `mcp__github__*`. Its report left the prompt out | 605k (492k) | $0.0326 |

The control tower checked the routine with its own `get`, which echoed the prompt three times. So the skills run the agent this way, and never through the `Agent` tool, and run-batch's fork fallback for a failed `create` went. One `create` cost the agent about $0.03 at haiku, so some $0.20 for six, where the fork of batch #153 spent 486k tokens at the control tower's model on six.

## The spike's code

The agent above is the whole spike: the throwaway plugin around it held only a `plugin.json` with its name, and lived outside the repository. So nothing was left to keep on a throwaway branch.
