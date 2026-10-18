# agent-kit

A way to build software where Claude Code agents do the development and the testing, and a human owner decides what gets built.

- **[SPEC.md](SPEC.md)**: the process, and the source of truth. It covers how work is planned, run unattended, verified, reviewed and merged.
- **`plugin/`**: the Claude Code plugin that implements it. Today it holds `agent-batch`, the batch runner.
- **`template/`**: the skeleton for new projects.

## Status

| Part | State |
|---|---|
| Spec | Written |
| Batch runner, `agent-batch` | Built and tested; not yet run against real Claude and GitHub |
| Plugin skills and hooks | Next |
| Project skeleton and the Python preset | Planned |

## The batch runner

It needs git, the GitHub CLI (`gh`) and Claude Code (`claude`), both signed in, and [uv](https://docs.astral.sh/uv/). Until the plugin is installed, call it as `plugin/bin/agent-batch`.

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

SPEC §5, §9 and §11 explain how a batch runs, what merges by itself and what waits for the owner.

## Developing the kit

```bash
make setup   # the pinned Python and tools, through uv
make check   # format, lint, types, layers, complexity, size limits, tests with coverage, audit
make test    # the tests only
```

Every change goes through an issue and a pull request, and the owner merges it (SPEC §16).
