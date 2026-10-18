# agent-kit

A way to build software where Claude Code agents do the development and the testing, and a human owner decides what gets built.

- **[SPEC.md](SPEC.md)**: the process, and the source of truth. It covers how work is planned, run unattended, verified, reviewed and merged.
- **`plugin/`**: the Claude Code plugin that implements it: `agent-batch`, the batch runner, and the hooks.
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

## Install

It needs git, the GitHub CLI (`gh`) and Claude Code (`claude`), both signed in, and [uv](https://docs.astral.sh/uv/).

**Install it per project, never for your user.** Its rules belong to projects that follow this process, and `claude plugin install` installs for the user unless told otherwise. From the project's folder:

```bash
claude plugin marketplace add lucastkacz/agent-kit --scope project
claude plugin install agent-kit@agent-kit --scope project --config language="English"
```

That writes the marketplace and `"enabledPlugins": {"agent-kit@agent-kit": true}` into the project's `.claude/settings.json`; commit it. If the plugin ends up installed for the user anyway, its hooks still act only in projects whose settings enable it.

`--config` is the exception: Claude Code keeps plugin options in your user's settings, so `language` goes into `~/.claude/settings.json`, as `"pluginConfigs": {"agent-kit@agent-kit": {"options": {"language": "English"}}}`. It does nothing in projects that don't enable the plugin. To change the language, edit that value there; it applies from the next session on.

Then start a new session in the project. `agent-batch` joins the PATH, and the hooks start working: they keep commits and pushes off `master`, show what waits for you when a session starts, and log permission denials. `language` is the language Claude talks to you in.

## The batch runner

```bash
agent-batch run 12              # run the batch whose tracking issue is #12
agent-batch run 12 --lanes 3    # 3 lanes at a time
agent-batch ship 15 --title "feat: export cards" --body-file pr.md   # direct mode
```

A batch's tracking issue lists its lanes. Two optional lines set the lanes at a time (2 by default) and the budget:

```
Lane 1: #12, #15
Lane 2: #13
Lanes: 2
Budget: 4 issues, 3 hours
```

During a batch, leave the Mac plugged in with its lid open. The runner keeps it awake only on AC power, and says so at the start when it's on battery; closing the lid sleeps it anyway.

SPEC §5, §9 and §11 explain how a batch runs, what merges by itself and what waits for the owner.

## Developing the kit

```bash
make setup   # the pinned Python and tools, through uv
make check   # format, lint, types, layers, complexity, size limits, tests with coverage, audit
make test    # the tests only
```

Every change goes through an issue and a pull request, and the owner merges it (SPEC §16).
