# agent-kit

AI agents build and test the software. A person, the owner, decides what gets built and approves what ships.

agent-kit is a plugin for Claude Code and the process behind it: the owner spends their attention on choosing the work and accepting the result, and the agents do everything in between, unattended.

## How it works

Work moves in batches. The owner and an assistant plan a batch together, the agents work through it while the owner is away, and then the two of them go over the result.

```mermaid
flowchart LR
    plan["Plan a batch<br/>owner and assistant"] --> work["Agents work it<br/>unattended"]
    work --> accept["Accept the result<br/>owner and assistant"]
    accept -->|next batch| plan
```

Each issue in a batch follows the same path. Tests come first, a separate reviewer checks the change, and only the risky changes wait for the owner.

```mermaid
flowchart LR
    ready["Issue ready"] --> tests["Tests first"]
    tests --> build["Implementation"]
    build --> review["Review"]
    review -->|changes| build
    review -->|approved| pr["Pull request"]
    pr --> risk{"Risk?"}
    risk -->|low| auto["Merges by itself<br/>once checks pass"]
    risk -->|high| owner["The owner merges it"]
```

## What it does

- **Guardrails it enforces:** agents never push to the main branch, never read secrets, and build nothing outside an approved issue, and a batch's agents never merge. These are blocked by rules and code, not just asked for. In a session, an agent merges a pull request only when the owner asks for that one.
- **Quality it checks:** every criterion that can be automated has a test, written before the code. Formatting, linting, types, size and complexity limits, coverage and a dependency audit run on every change.
- **What waits for the person:** the questions only the owner can answer, the high-risk changes to merge, and the checks that need human eyes. Everything else keeps moving.

## Learn more

- [SPEC.md](SPEC.md): the whole process, and the source of truth.
- [docs/usage.md](docs/usage.md): requirements, install, the batch runner, and developing the kit.
