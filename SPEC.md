# agent-kit spec

How to build software where Claude Code agents do the development and the testing, and a human owner decides what gets built.

This document is the source of truth. The plugin, the runner, the presets and the project skeleton in this repository implement it; when they disagree with it, they are wrong and get fixed.

## Contents

1. [Principles](#1-principles)
2. [Roles](#2-roles)
3. [The rhythm](#3-the-rhythm)
4. [Work items](#4-work-items)
5. [The issue pipeline](#5-the-issue-pipeline)
6. [Contexts](#6-contexts)
7. [Verification](#7-verification)
8. [Code quality](#8-code-quality)
9. [Risk and merging](#9-risk-and-merging)
10. [Permissions and safety](#10-permissions-and-safety)
11. [Unattended batches](#11-unattended-batches)
12. [Delegating to the cloud](#12-delegating-to-the-cloud)
13. [Project skeleton](#13-project-skeleton)
14. [Conventions](#14-conventions)
15. [Documentation](#15-documentation)
16. [Changing the process](#16-changing-the-process)
17. [Out of scope](#17-out-of-scope)
18. [Open questions](#18-open-questions)
19. [Glossary](#19-glossary)

## 1. Principles

1. **The owner decides what and why; agents decide how.** The owner approves scope and accepts results. Everything in between is the agents' work. Human attention is the scarcest resource, and approving mechanics (each command, each step's plan) spends it without adding judgment.
2. **Approve once, then never wait.** The owner approves a batch of issues in one sitting. During the batch no agent stops for a person: a question is written down, and work moves on to the next issue.
3. **Nothing gets built outside an approved issue.** Work found along the way becomes a new issue for the owner to decide on.
4. **Guardrails are mechanisms, not prose.** What must never happen is blocked by permission rules, hooks, GitHub rulesets or the runner's code, and every guardrail has tests. Text guides; it doesn't protect.
5. **A guardrail must fit how agents actually work.** A check that blocks legitimate work is a bug: it makes the owner wait and teaches everyone to route around it. Guardrails are tested against the commands agents really run.
6. **Automate verification.** Every acceptance criterion is checked by a test, unless it needs a human for one of a few listed reasons. A manual check is the exception, and it says why it can't be automated.
7. **Never take over the owner's machine.** Agents test in the background, and the owner keeps using the computer while they work.
8. **Security first.** Secrets and real data stay with the owner. Agents never read secrets, never touch real data, and never run with credentials that can do real damage.
9. **Keep high risk narrow and its gate strong.** Only what can really hurt waits for the owner. If everything is high risk, everything waits again.
10. **Few contexts, lean instructions.** Every new agent context re-reads its instructions and the code. Contexts are added only when independence pays for them, and always-loaded instructions stay short.
11. **Standard practices first.** GitHub issues, pull requests and rulesets, established style guides, Conventional Commits, ADRs. Our own inventions are few, and each one says why it exists.
12. **Professional code, enforced by tools.** The bar is code a senior engineer would be glad to maintain. What a tool can check, a tool checks.
13. **Always say the next step.** Every exchange with the owner ends with one next action, in plain words.

## 2. Roles

| Role | Who | Does | Never |
|---|---|---|---|
| **Owner** | The human | Brings ideas, answers questions, approves batches, does the human checks, merges high-risk PRs, holds secrets and real data. | |
| **Assistant** | Claude, in an interactive session with the owner | Plans batches, works in direct mode, starts and watches batches, runs acceptance. | Merges, reads secrets, builds outside approved issues. |
| **Runner** | `agent-batch`, a script | Orchestrates batches: launches agent runs, pushes branches, opens PRs, classifies risk, merges low-risk PRs, labels issues, notifies. | Decides what to build. |
| **Implementer** | A Claude run per lane | Writes the acceptance tests, implements, runs the checks, writes the PR body. | Pushes, merges, edits outside its worktree. |
| **Reviewer** | A Claude run per issue, read-only | Checks the change against its issue and this spec, then approves or asks for changes. | Edits anything. |

The runner is code, not a model, because the decisions that must come out the same every time (when to merge, what to label, when to stop) belong in tested code.

## 3. The rhythm

Work moves through three moments, plus a shortcut for small changes. The owner's attention goes where it matters (choosing and accepting), and agents never wait for it.

### 3.1 Planning: owner and assistant

- The owner describes the idea. The assistant asks only the questions that change what gets built, one topic at a time.
- The assistant writes the issues (§4) and proposes the batch: which issues, in which lanes, with what budget, which of them go to the cloud (§12) and what that gains, and the model and effort, with the owner's own settings as the default.
- Issues that touch the same files share a lane, in order; the others get lanes of their own. A high-risk issue goes last in its lane or alone, and when every issue is high risk, one per lane (§11.1). `Lanes:` is the number of independent lanes.
- The owner approves the batch as a whole. Only then does the assistant label its issues `ready`.

### 3.2 The batch: agents, unattended

- The owner starts it. The runner works through the lanes (§11) while the owner is away or busy with something else.
- Nothing prompts. A decision that needs the owner becomes a `blocked` issue with the question written down, the owner gets a notification, and the batch continues. An issue whose run fails is labeled `blocked` too, with what went wrong, so no batch retries it blindly.
- Low-risk PRs merge by themselves once CI is green. High-risk PRs wait.
- At the end, the batch issue gets a summary and the owner gets a notification.

### 3.3 Acceptance: owner and assistant

In one sitting, the assistant walks the owner through:

1. What merged.
2. The high-risk PRs, each with a short explanation and a link to merge it.
3. The blocked questions. The owner answers; the assistant writes each decision into its issue and removes `blocked`, so the issue is ready for the next batch.
4. The batch's human checks, as one checklist.
5. The run's permission denials and friction, turned into proposed changes to the project or to this kit.
6. The batch's numbers (§16.2), to see whether the process is getting better.

### 3.4 Direct mode

For a small change while the owner is present, the same pipeline (§5) runs inside the session, without a batch. It still starts from an issue, still writes the tests first, and still goes through the reviewer and the runner's merge gate (`agent-batch ship <issue>`).

### 3.5 Where the owner stands

Every session starts by showing what waits for the owner: blocked questions, high-risk PRs, a pending acceptance, a running batch.

## 4. Work items

All work is tracked in GitHub.

### 4.1 Issue types

Each type has an issue form. Blank issues are disabled.

- **Task:** work to build.
  - *Goal:* what changes for the user, in one or two sentences.
  - *Why.*
  - *Briefing:* the files, interfaces and decisions the implementer needs, so it doesn't have to rediscover them.
  - *Acceptance criteria:* observable behaviors, each with how it is verified (§7.1).
  - *Out of scope.*
  - *Stop and ask if:* the situations where an agent must not decide alone.
  - *Risk:* low or high, and why (§9).
- **Bug:** what happened, what was expected, the steps to reproduce, and the PR that introduced it when known. That last field shows how often problems get past the pipeline.
- **Idea:** what, why, and the open questions. Ideas are not built; planning turns them into tasks.
- **Spike:** a question to answer before building, such as whether an approach or a library works. It has a time box and ends in an ADR with the answer. The ADR is merged; the code stays on a throwaway branch and is never merged.

### 4.2 Labels

| Label | Meaning |
|---|---|
| `task`, `bug`, `idea`, `spike` | The issue's type. |
| `ready` | The owner approved it for a batch. |
| `blocked` | Waiting on a decision of the owner's. The question is in the issue's latest comment. |
| `needs-human` | The owner asked to review it, or it has human checks. |
| `risk:high` | The owner merges it (§9). |
| `batch` | A batch's tracking issue. |

### 4.3 Batches

A batch is a milestone plus a tracking issue labeled `batch`:

- The milestone groups the batch's issues.
- The tracking issue holds the lane plan, the budget, the live status, the final summary and the acceptance checklist. It exists because milestones can't hold a conversation.

The lane plan lists each lane's issues in order. Optional lines add the rest:

- `Lanes:` how many lanes run at a time (§11.1).
- `Budget:` the issues and hours the batch may spend (§11.2).
- `Model:` the model of the batch's runs, then optionally a comma and their effort: `low`, `medium`, `high`, `xhigh` or `max`. The model is an alias, such as `opus`, or a full model name. Without the line, the runs use the owner's own settings (§11.1).
- `Cloud:` the issues worked in the cloud (§12), which are in no lane. The `run-batch` skill reads it; the runner ignores it.

The runner reads `Lanes:`, `Budget:` and `Model:`, and refuses a batch whose `Lanes:` or `Model:` line it can't read.

```
Lane 1: #12, #15
Lane 2: #13
Lane 3: #14
Lanes: 3
Budget: 4 issues, 3 hours
Model: opus, high
Cloud: #16
```

### 4.4 Ready

An issue is ready when all of these hold:

- It was opened by the owner (§10.6). Issues the assistant writes during planning count, since it works under the owner's account.
- It has a goal, criteria with their verification, and a risk.
- It has no open question.
- The owner approved its batch.

Agents take only ready issues.

### 4.5 Work found along the way

Bugs, ideas and improvements found while working become new issues without `ready`, linked from the PR ("Found while working on #N"). They are never folded into the current PR.

## 5. The issue pipeline

The same steps run in a batch and in direct mode.

1. **Worktree and branch.** Each lane has its own worktree. Each issue gets a branch `<issue>-<short-name>` in it, from the latest `origin/master`; if the branch already exists from an earlier batch, its work is picked up. In direct mode, the branch is wherever the assistant works.
2. **Acceptance tests first.** The implementer writes a test for each automatable criterion and commits them on their own (`test: acceptance tests for #N`). They fail, for the right reason. They are formatted before that commit, and after it they don't change: a later test goes in a file of its own. If one looks wrong, the issue is blocked with the question. When the test is indeed wrong, the owner can approve fixing it inside the acceptance commit and rebuilding the branch on `master`.
3. **Implementation,** until `make check` passes, quality gates included (§8).
4. **Visible behavior.** `make e2e` for UI criteria, keeping its evidence.
5. **Review.** A separate, read-only run (§6) checks the branch against the issue, §7 and §8. `changes` sends the findings back to the implementer. After two rounds without approval, the issue is blocked.
6. **Pull request.** The runner pushes the branch and opens the PR from the template, with `Closes #N`. The implementer writes the body.
7. **Risk and merge.** The runner classifies the risk (§9). Low: auto-merge armed, squash, pinned to the reviewed commit. High: label `risk:high`, and the owner merges.
8. **Cleanup.** The merged branch is deleted, and the lane's worktree is removed when the lane ends.

## 6. Contexts

Every new context re-reads its instructions and the code it touches, which costs time and usage. A batch uses two kinds:

- **One implementer per lane.** Issues in a lane touch the same files, so the implementer resumes the same session from one issue to the next instead of starting over. After a few issues (default 3) it starts fresh, because quality drops as a context fills up.
- **One reviewer per issue, fresh on purpose.** A reviewer that inherits the implementer's reasoning inherits its mistakes too. It reads the diff, the issue and the checks of §7 and §8, so it is cheap.

There are no other subagents by default: no researchers, no explorers. Research is a task of its own, planned like any other.

Two more savings:

- **The issue is the briefing.** Planning writes down the files, interfaces and decisions, so agents don't rediscover them.
- **Lean always-loaded instructions.** A project's `CLAUDE.md` stays short (§15), because every context pays for it in full. The process lives in skills, and language rules in files that load only when they are needed.

## 7. Verification

### 7.1 Every criterion says how it is verified

- `unit`, `integration` or `e2e`: a test in the repository.
- `human(<reason>)`, only for one of these reasons:
  1. **Taste:** whether it looks or feels right. Whether the layout is correct is testable; whether it is pleasant is not.
  2. **Physical hardware,** or an operating-system permission dialog.
  3. **Real accounts, real money or real personal data.**
  4. **A third-party service without a test environment.**

The reviewer blocks when a criterion has no test, when a `human` item could be automated, or when the acceptance tests changed after their commit.

### 7.2 Background only

Agents never bring an app to the front and never use the owner's mouse or keyboard. In order of preference:

1. **Below the UI:** logic in a pure core, tested directly.
2. **Snapshot tests:** the view is rendered to an image inside the test, with no window. Layout, sizes, zoom, themes and contrast can be checked this way.
3. **Driving the app in the background,** through accessibility or automation APIs that work without focus, and capturing its window alone.
4. **Real focus,** only when the owner hands over the screen for a batch (§11.4) or inside a virtual machine. Otherwise the check goes to the human list.

For web apps (a headless browser) and command-line tools, this comes naturally.

### 7.3 Fast and proportionate checks

An agent runs the tests dozens of times per issue, so the speed of the tests is the speed of development.

- **Test sizes.** Small tests touch no files, network or other processes, and take milliseconds. Medium tests use local resources, such as a temporary folder or a local database. Large tests drive the running app. `make test` runs the small and medium ones; `make e2e` runs the large ones.
- **Time budgets.** `make test` finishes in under 30 seconds, and `make check` in under 5 minutes. A project that goes over gets a task to bring it back.
- **Proportionate.** Checks fit the change. No mutation testing, no fan-out of parallel test processes that saturate the machine, and every check has a time limit. Review goes deep on high-risk changes and stays light on trivial ones.

### 7.4 Testability by design

- Logic lives in a pure core. Files, network, OS services and UI stay thin, at the edges.
- Time, randomness and the environment are injected, never read directly by the logic.
- Development builds are separate from real data: their own identity, data folder and settings.
- Every interactive control has a stable identifier.
- Fixtures are made by hand, never copied from real data.

### 7.5 An isolated instance per lane

Parallel lanes share no running state. Each lane runs its own instance, with its own data, identity and ports: another port and database for a web app, another data folder for a command-line tool, another bundle identifier for a desktop app.

### 7.6 Evidence

The PR shows what was run and what it returned: the check summary, the e2e results, and the snapshots or window captures for visual criteria.

### 7.7 Property-based tests

Logic with many possible inputs, such as parsing, calculations or state machines, gets property-based tests on top of examples: the test generates hundreds of cases and checks what must always hold. They find the edge cases nobody thought to write down.

## 8. Code quality

A rule that a tool checks is followed every time and costs no context. A rule written in prose is followed loosely and loaded into every context that needs it. So most of this section is enforced by tools, and prose covers only what tools can't.

### 8.1 Three layers

| Layer | What | When |
|---|---|---|
| **Local** | Formatter, strict linter, strict type checker, size and complexity limits, architecture boundaries, tests with coverage of new code, dependency audit | `make check`, in seconds, on every change |
| **GitHub** | CodeQL code scanning, Dependabot alerts, secret scanning with push protection, dependency review on every PR, OpenSSF Scorecard | On every PR and every push to `master` |
| **Review** | The reviewer's rubric (§8.6) | Once per issue |

The local layer is the main one: an agent gets its findings in seconds and fixes them before review, so review can focus on design and logic. The GitHub layer is a second net, free for public repositories and with no extra accounts. External quality and security platforms are not part of the base: they duplicate these layers and add accounts and tokens.

### 8.2 Limits

| Limit | Default |
|---|---|
| Lines per source file | 400 |
| Lines per function | 50 |
| Cognitive complexity per function | 15 |
| Parameters per function | 5 |
| Coverage of new and changed code | 80% |
| Type checking | Strict |
| Warnings | Treated as errors |

Small files and functions are easier to review and cheaper for agents: a file is read whole without filling a context, edits are precise, and parallel lanes collide less. Generated code and test fixtures are exempt. A project changes a default only with an ADR that says why.

Coverage is a floor, not a goal. A test that only raises coverage is noise, and the reviewer treats it as such.

### 8.3 No silenced rules

A rule is never silenced to make a check pass. When an exception is truly needed, the suppression names the rule and gives the reason on the same line, and the reviewer judges it. A rule that is wrong for the project is changed in the configuration, with its reason, not silenced line by line.

### 8.4 Style guides

Each language follows an established guide, referenced rather than copied:

- **Python:** [PEP 8](https://peps.python.org/pep-0008/), [PEP 257](https://peps.python.org/pep-0257/) and the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).
- **TypeScript:** the [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html).
- **Swift:** the [Swift API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/).
- **Others:** the language's official guide, or else [Google's](https://google.github.io/styleguide/).

As much of a guide as possible becomes linter configuration. What remains, plus the project's own conventions, goes in one short rules file per language, which loads only when an agent touches that language's code.

### 8.5 Design and structure

- **Functional core, imperative shell** (also known as ports and adapters). Logic lives in a pure core; input and output, frameworks and UI live in thin adapters around it. The core never imports an adapter, and a tool checks it.
- **Predictable layout.** One concept per file. The folder layout is the same in every project of a stack, set by its preset (§8.8). Tests mirror the source tree.
- **Explicit over clever.** No metaprogramming, reflection or dynamic dispatch that hides who calls what. Everything can be found with a plain text search.
- **One concept, one name.** Names come from the product's vocabulary (§15).
- **Errors say what happened and what to do.** They are typed. Unexpected data fails loudly; nothing guesses a default for what it doesn't know.
- **Comments explain a non-obvious why,** never what the code does. No dead or commented-out code.
- **Only what the issue needs.** No speculative abstractions, options or extension points.
- **Few dependencies.** Each one is pinned, its lockfile is committed, and adding one needs an ADR (it is also high risk, §9.1).
- **Structured logs.** Every component logs its state changes and errors as structured records with a level, so an agent can reconstruct what happened from the logs instead of asking the owner to reproduce it. Logs never hold secrets or personal data.
- **A reproducible environment.** The toolchain, the tools and the dependencies are pinned, and `make setup` builds the whole environment from a clean checkout. The same command works on the owner's computer, in a new worktree, in CI and in the cloud.

### 8.6 The review rubric

The reviewer follows Google's [code review guide](https://google.github.io/eng-practices/review/reviewer/): design, functionality, complexity, tests, naming, comments, style and documentation. On top of that come the verification checks of §7, and the [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) for anything that handles input, secrets or the network.

Only what affects correctness, security, the acceptance criteria or this section blocks a change. Everything else is a suggestion that never blocks, because chasing every finding leads to over-engineering.

### 8.7 Machine-readable output

Every tool in `make check` can report in a machine-readable form, such as JSON or SARIF, so agents act on findings without parsing prose.

### 8.8 Stack presets

What is concrete about a stack lives in a preset in this kit (`presets/<stack>/`): its tools and their configuration, the folder layout, the CI setup, the `Makefile` commands, and a language server configuration, so agents see type errors as they edit and jump to definitions without a text search. `new-project` applies one. A preset is added when a real project needs it.

**No preset, no start.** When a project's stack has no preset, `new-project` says so and stops. The first task is to write the preset here, in a PR the owner merges, and only then is the project created. The same applies when an existing project brings in a new language or stack: the work that needs it is blocked until its preset exists. A project with several stacks, such as a backend in one language and a frontend in another, needs a preset for each.

Why: a project that starts without its tools and rules starts without its quality gates, and adding them later means reworking code that was written without them.

## 9. Risk and merging

### 9.1 High risk

A change is high risk when it touches:

- secrets, credentials, real accounts or real data;
- the agents' own controls: `.claude/`, hooks, `.github/`, the `Makefile`, scripts, the quality configuration;
- dependencies, new or updated;
- database schemas and migrations;
- anything irreversible: deletions, data migrations, writes to external systems;
- a path listed in the project's `.claude/risk-paths`.

Everything else is low risk. The list is narrow on purpose (principle 9).

### 9.2 Who merges

- **Agents never merge.** A permission rule denies `gh pr merge` and merge API calls to every Claude session.
- **Low risk:** once the reviewer approves, the runner arms auto-merge (squash, pinned to the reviewed commit). GitHub merges when CI is green.
- **High risk:** the runner labels the PR `risk:high` and leaves it for the owner. No agent ever removes that label.
- **Dependency updates:** one grouped PR a month, high risk.

### 9.3 Enforced by GitHub

Every repository protects `master` with a ruleset: changes go through a PR, the `check` status and the code scanning results must pass, and force pushes and deletion are blocked. Rulesets and auto-merge are available for public repositories on every GitHub plan. A local hook also blocks commits and pushes to `master`.

## 10. Permissions and safety

### 10.1 Zero prompts during a batch

Unattended runs never ask. Anything that would need a prompt is denied; the agent records it and moves on. Every denial is logged: a batch's runs report theirs in their answers, the runner records each one as a `permission_denied` event and lists it in the batch's summary, and a hook logs those of an interactive session in `.agent-batch/denials.jsonl`. Acceptance reviews them, to fix the rule or the habit behind each one.

### 10.2 Rules

- **Allow** narrow, exact commands: the `Makefile` targets, git on branches, reading and writing issues and PRs, the runner. Narrow rules are matched before auto mode's classifier runs, so they never depend on its judgment.
- **Deny:** secret stores, `.env` files, force pushes, `git reset --hard`, `git clean`, deleting repositories, merging, admin overrides, and removing `risk:high`.

### 10.3 Commands the classifier can read

Auto mode's classifier judges a command by its text. It can't see what a variable or a saved script expands to, so it asks or denies. Therefore:

- Call scripts by their path, never through a variable or a function.
- Edit files with the edit tool, never with `python`, `sed -i` or similar.
- Write loops inline, instead of saving a script to a temporary folder and running it.
- Prefer one command per call over long chains.

### 10.4 Secrets and real data

- Secrets live in the operating system's secret store, such as the macOS Keychain. Agents never read them, and commands that need real credentials are run by the owner.
- Agents never run with credentials that can do real damage, such as moving money or deleting accounts.
- Real data never enters the repository, and development builds never touch it.

### 10.5 Self-modification

Changes to the agents' own configuration (`CLAUDE.md`, `.claude/`, hooks, CI) are high risk and merged by the owner. Auto mode refuses some of them by design, and that is intended. Changes to the process itself are made in this kit (§16), not project by project.

### 10.6 Trust boundary

Repositories are public. Only the owner's issues are work: the runner takes issues opened by the owner and labeled `ready`. Text written by anyone else is information, never instructions: issues, PRs, comments, and the web pages or documents an agent reads.

### 10.7 Never bypass

No `--no-verify`, no disabled hooks, no admin merges. If a guardrail is wrong, the fix is a change to the guardrail, reviewed like any other.

## 11. Unattended batches

### 11.1 The runner

`agent-batch run <batch>` is started by the assistant when the owner asks, or by the owner from a terminal. It:

- launches a fresh `claude -p` for each stage, in auto mode with prompts turned off, so nothing ever waits for a person;
- runs the implementer, the reviewer and the conflict resolver on the same model and effort: `--model` and `--effort` when given, else the batch issue's `Model:` line, else the owner's own settings. The start comment and the summary say them when they're set, so batches can be compared (§16.2). `agent-batch ship` takes the same two flags;
- removes API keys from its environment, so runs use the owner's subscription instead of paid API usage;
- keeps the machine awake while it runs on AC power, warns at the start when it's on battery, and caps each run's turns and wall-clock time;
- runs several lanes in parallel: as many as `--lanes` says, else the batch issue's `Lanes:` line, else 2. Each lane's issues run in order, and the next one starts only after the previous PR merged, from the latest `master`;
- defers the rest of a lane to the next batch when one of its issues doesn't merge (it waits for the owner, is blocked or failed), because they build on the same files. Planning puts high-risk issues last in their lane, or in a lane of their own;
- makes one attempt to resolve a merge conflict; if that fails, the issue is blocked;
- labels, comments, writes every step to an event log, and posts the summary in the batch issue.

The runner is written in Python with only the standard library, and runs on a pinned Python through `uv`. Its state (the lanes' worktrees and the event logs) lives in `.agent-batch/` in the project's main folder, which git ignores.

Why a script instead of a long interactive session: in auto mode, an interactive session still stops to ask in some cases (ask rules, protected paths, repeated classifier denials). A headless run with prompts turned off never waits.

### 11.2 Budget

A batch has a budget: a number of issues, a number of hours and, when the subscription's usage can be read, a share of it. Near the budget, the runner finishes the issues in progress, starts no new ones, and notifies the owner. Hitting the subscription's usage limit stops the batch the same way; the issue that was cut off keeps `ready` and goes to the next batch.

### 11.3 The control tower and notifications

The interactive session that started the batch watches the runner's log. It sends the owner a phone notification when an issue is blocked, when the budget is reached and when the batch ends. If that session closes, the runner keeps going, and the batch issue still gets its summary.

### 11.4 Using the screen

By default nothing takes the screen (§7.2). `--screen` allows the checks that need real focus, for a batch the owner starts before leaving the computer.

### 11.5 Nothing starts by itself

The owner starts every batch. There are no scheduled or recurring runs.

### 11.6 Engines

The runner's engine decides where agent runs happen: `local`, on the owner's computer (the default), or `cloud` (§12).

## 12. Delegating to the cloud

Claude Code can also run in a virtual machine in Anthropic's cloud instead of the owner's computer. The session clones the repository, works on a branch and opens a PR, using the owner's subscription. The owner's computer stays free, sessions run in parallel, each in its own machine, and since each machine is isolated, no prompts are needed.

**Good for the cloud:**

- implementing issues of projects that build and test on Linux: web apps, command-line tools, libraries, services;
- research and spikes that end in an ADR;
- reviewing PRs;
- maintenance: dependency updates, fixing CI, adding missing tests, refactors;
- turning ideas captured from a phone into issues, without `ready`.

**Stays local:**

- native apps, and anything that needs the platform's own frameworks or tools;
- anything that uses the owner's apps, files or devices;
- real data, real accounts and secrets;
- planning and acceptance, which happen with the owner.

**Same rules:** ready issues only, tests first, review, a PR, and merging by risk. No real secrets in cloud environments, and network access limited to GitHub and package registries.

## 13. Project skeleton

`new-project` creates a repository from `template/` and the stack's preset (§8.8). It creates the GitHub repository with its labels and ruleset, turns on CodeQL, secret scanning with push protection, Dependabot alerts and private vulnerability reporting, and opens the project once interactively so that its settings are trusted.

**The plugin is enabled per project, never for the user.** The project's `.claude/settings.json` declares the marketplace and enables the plugin, and the project commits it. Installed for the user, the plugin's rules would reach projects that follow other ones. That's why its hooks act only in projects whose settings enable it, even when it's installed for the user by mistake.

### 13.1 Files

- `CLAUDE.md`: the product in two lines, the stack, the commands, the project's risks, and how it is published. Short (§15).
- `.claude/settings.json`: the permissions of §10.2, and the plugin.
- `.claude/risk-paths`: the project's high-risk paths. The runner reads them from `master`, where no agent of the running batch can change them.
- `.gitignore`: includes `.agent-batch/`, the runner's state.
- `.claude/rules/<language>.md`: the language's rules beyond its guide and linter (§8.4).
- `.github/ISSUE_TEMPLATE/`: the task, bug, idea and spike forms, with blank issues disabled.
- `.github/pull_request_template.md`: summary, `Closes #N`, a verification table (criterion, test, result), evidence, human checks with their reasons, the reviewer's verdict, and the risk.
- `.github/workflows/check.yml`: runs `make check` on PRs and on `master`, and dependency review on PRs. It cancels superseded runs, skips docs-only changes, has a timeout, pins actions by commit SHA and doesn't persist credentials.
- `.github/dependabot.yml`: monthly, grouped into one PR, labeled `risk:high`.
- `.github/workflows/scorecard.yml`: runs OpenSSF Scorecard on pushes to `master` and publishes the score.
- `SECURITY.md`: how to report a vulnerability privately.
- `Makefile`: the contract below.
- The preset's tool configuration.
- `docs/product.md` and `docs/adr/`.

### 13.2 The Makefile contract

The same targets in every project, whatever the stack:

| Target | Does |
|---|---|
| `make setup` | Builds the environment from a clean checkout, with pinned versions. |
| `make check` | Everything in §8.1's local layer, plus the build. Exactly what CI runs. Under 5 minutes. |
| `make test` | The small and medium tests (§7.3). Under 30 seconds. |
| `make fmt` | Formats the code. |
| `make e2e` | The large tests: drives the running app in the background (§7.2) and checks its visible behavior. |
| `make run` | Runs the development build. |

## 14. Conventions

- Everything in the repository and on GitHub is in English. Conversations with the owner are in the owner's language, set in the plugin's configuration.
- The default branch is `master`.
- Branches are named `<issue>-<short-name>`.
- One issue, one PR, kept small.
- PR titles follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`, `build:`). PRs are squash-merged, so each one lands on `master` as a single commit named after its title.
- The PR body says `Closes #N`.

## 15. Documentation

A document exists only if it has a unique purpose, a concrete reader, and content that can't be derived from the code, the tests or the history.

- **`CLAUDE.md`:** short, because it is loaded into every context.
- **`docs/product.md`:** what the product does, for whom, and the words it uses for things. The source of truth for behavior and for names.
- **`docs/adr/NNNN-title.md`:** one short record per significant decision, with its context, the decision and its consequences.
- **`.claude/rules/<language>.md`:** short, loaded only when that language's code is touched.
- **No session notes, plans, reports or summaries in the repository.** Plans live in issues; what was done lives in PRs and the history.
- **A change that makes a document stale fixes it in the same PR.**

## 16. Changing the process

### 16.1 How it changes

- The process changes here: first this document, then the kit that implements it, through a PR on this repository that the owner merges.
- Projects pick up the new version when the plugin updates.
- Friction found during acceptance becomes an issue here, with its evidence: the denial log, the blocked question, the step that went wrong.

### 16.2 Measuring it

Every batch records its numbers in its tracking issue, and acceptance compares them with earlier batches:

- issues done, blocked and failed;
- review rounds per issue;
- human checks;
- permission denials. The goal is zero prompts and few denials;
- escaped bugs: bugs whose "introduced by" field points to a PR of a recent batch;
- time from approval to merge;
- usage spent.

A number that gets worse is friction, and friction becomes an issue here.

### 16.3 Testing the kit

The kit is code, and the most important code: when it breaks, every project breaks.

- **Fast tests, on every change.** The runner and the hooks are tested against fake `claude` and `gh` commands, so `make check` stays fast and runs in CI.
- **Contract tests, on demand.** `make contract` runs the real `claude` and `gh` through the runner's own adapters, on this repository, and records their answers. The owner runs it, since it writes to GitHub and uses the subscription. `make check` then compares the fakes' answers with the recordings, field by field, so a fake that drifts from the real tool fails a test.
- **Behavior tests for the skills,** run with Claude Code's plugin evaluations.

A change to the kit merges only when they pass.

## 17. Out of scope

In this version:

- **Releasing and deploying.** The process ends at the merge to `master`. Each project writes down how it publishes in its `CLAUDE.md`.
- **Scheduled or recurring runs.**
- **Presets other than Python.** Each one is written when a real project needs it, before that project starts (§8.8).

## 18. Open questions

To settle while building the kit:

- Whether a headless run can read the subscription's usage, for the budget's share limit.
- Whether the control tower's phone notifications work as described.
- How the cloud engine dispatches issues and brings their PRs back to the merge gate. This gets tried on a project that builds on Linux.
- Whether language servers (§8.8) and plugin evaluations (§16.3) work as described here.
- Whether headless runs in a lane's worktree pick up the project's own permission rules, which apply only in a trusted folder. The contract tests settled the rest: a run's JSON, resuming a session from the same folder, the reviewer's denials, and the batch settings' deny rules.

## 19. Glossary

- **Owner:** the person who decides what gets built and accepts it.
- **Batch:** a set of ready issues, approved together and run unattended.
- **Lane:** the issues of a batch that touch the same files, run in order.
- **Runner:** `agent-batch`, the script that orchestrates batches and merges low-risk PRs.
- **Engine:** where agent runs happen, local or cloud.
- **Control tower:** the interactive session that watches a batch and notifies the owner.
- **Direct mode:** the pipeline run inside an interactive session, for a small change.
- **Acceptance:** the session where the owner reviews a batch's results.
- **Preset:** the concrete tools, configuration and layout for one stack.
- **Spike:** a time-boxed question, answered with an ADR. Its code is never merged.
