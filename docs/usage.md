# Using agent-kit

How to install the kit, run batches, and work on the kit itself. [SPEC.md](../SPEC.md) is the source of truth for the process; this page covers the mechanics.

## What's in the repository

- **[SPEC.md](../SPEC.md)**: the process. It covers how work is planned, run unattended, verified, reviewed and merged.
- **[`plugin/`](../plugin)**: the Claude Code plugin that implements it: `agent-batch`, the batch runner, and the hooks.
- **`template/`**, planned: the skeleton for new projects.

## Status

| Part | State |
|---|---|
| Spec | Written |
| Batch runner, `agent-batch` | Built; checked against the real `claude` and `gh` (`make contract`) |
| Plugin and hooks | Built |
| Plugin skills: implement and review | Built |
| Plugin skills: plan-batch, run-batch and accept-batch | Next |
| Project skeleton and the Python preset | Planned |

## Requirements

git, the GitHub CLI (`gh`) and Claude Code (`claude`), both signed in, and [uv](https://docs.astral.sh/uv/).

## Install

**Install it per project, never for your user.** Its rules belong to projects that follow this process, and `claude plugin install` installs for the user unless told otherwise. From the project's folder:

```bash
claude plugin marketplace add lucastkacz/agent-kit --scope project
claude plugin install agent-kit@agent-kit --scope project --config language="English"
```

That writes the marketplace and `"enabledPlugins": {"agent-kit@agent-kit": true}` into the project's `.claude/settings.json`; commit it. If the plugin ends up installed for the user anyway, its hooks still act only in projects whose settings enable it.

`--config` is the exception: Claude Code keeps plugin options in your user's settings, so `language` goes into `~/.claude/settings.json`, as `"pluginConfigs": {"agent-kit@agent-kit": {"options": {"language": "English"}}}`. It does nothing in projects that don't enable the plugin. To change the language, edit that value there; it applies from the next session on.

Then start a new session in the project. `agent-batch` joins the PATH, and the hooks start working: they keep commits and pushes off `master`, show what waits for you when a session starts, and log permission denials. `language` is the language Claude talks to you in.

The plugin also shows the batch's progress under the prompt, on one line that starts with `⚠ agent-kit:`: each running lane's and `ship`'s issue, step, and review round or minutes, such as `L1 #75 review 2/2 · L2 #66 implement 12m · ship #79 review 1/1`, or the branch when nothing runs. It shows only in a project whose settings enable agent-kit. It's `agent-batch status --line`, run every few seconds, which reads only the runner's state files. It needs Claude Code 2.1.287 or later; an older one leaves the line out.

## The batch runner

```bash
agent-batch run 12              # run the batch whose tracking issue is #12
agent-batch run 12 --lanes 3    # 3 lanes at a time
agent-batch run 12 --model opus --effort high   # every run on opus, at high effort
agent-batch ship 15 --title "feat: export cards" --body-file pr.md   # direct mode
agent-batch status              # what each lane and each ship is doing right now
agent-batch status --line       # the same in one line, as under the prompt
agent-batch clean               # delete the local branches whose PR merged
```

A batch's tracking issue lists its lanes. Optional lines set the lanes at a time (2 by default), the budget, and the model and effort of the batch's runs (your own settings by default; `--model` and `--effort` override them):

```
Lane 1: #12, #15
Lane 2: #13
Lanes: 2
Budget: 4 issues, 3 hours
Model: opus, high
```

During a batch, leave the computer plugged in, and on a laptop keep the lid open: closing it sleeps the computer anyway. The runner holds off sleep with `caffeinate` on macOS and `systemd-inhibit` on Linux, and says at the start when the computer is on battery, or when it can't keep it awake at all.

SPEC §5, §9 and §11 explain how a batch runs, what merges by itself and what waits for the owner.

## Developing the kit

```bash
make setup   # the pinned Python and tools, through uv
make check   # format, lint, types, layers, complexity, size limits, tests with coverage, audit
make test    # the tests only
```

Every change goes through an issue and a pull request, and the owner merges it (SPEC §16).
