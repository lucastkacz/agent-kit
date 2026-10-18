---
name: run-batch
description: Starts, runs or resumes a batch when the owner asks: starts `agent-batch run` for the lanes, sends the `Cloud:` issues to Anthropic's cloud, watches both as the control tower, ships each cloud branch, and notifies the owner's phone only when something needs them.
---

# Run a batch

You are the control tower (SPEC §11.3): you start the batch, watch it, and call the owner only when something needs them. Talk to the owner in ${user_config.language}, in plain words; everything on GitHub stays in English.

The batch is the tracking issue the owner names, else the open issue labeled `batch`. Its number is `<batch>` below.

## Read the plan

- Run `gh issue view <batch> --json title,body,milestone`.
- Read its lanes (`Lane 1: #12, #15`), and its `Lanes:`, `Budget:`, `Model:` and `Cloud:` lines. `Cloud: #20, #21` lists the issues that go to the cloud; `Model:` names the model, and maybe the effort, of the cloud runs and of their review. The runner ignores the lines it doesn't know.

## Check before starting

- Every issue of the plan, lanes and cloud, is labeled `ready` and not `blocked`: `gh issue view <n> --json labels,state`.
- `master` is clean and up to date: `git status --short` prints nothing, and after `git fetch origin master`, `git rev-parse master` equals `git rev-parse origin/master`.
- If something fails, tell the owner what and stop. Don't fix the plan yourself.

## Start

- When the plan has lanes, start `agent-batch run <batch>` in the background, with the `Bash` tool's `run_in_background`, so it keeps going while you watch. A batch with only a `Cloud:` line has no lanes, so the runner isn't started.
- In parallel, send each `Cloud:` issue to the cloud (below).

## Send an issue to the cloud

One routine per `Cloud:` issue, with the `RemoteTrigger` tool:

1. Fill `cloud-prompt.md`, next to this skill: `{repository}` is the project's `owner/name`, `{number}` and `{title}` the issue's, `{body}` its body verbatim, and `{branch}` the branch `<issue>-<short-name>`. The cloud's `gh` isn't signed in, so the body has to travel in the prompt.
2. `create` a one-time routine: `run_once_at` about 3 minutes ahead, the project's repository as its source, the tools `Bash`, `Read`, `Write`, `Edit`, `Glob` and `Grep`, the `Model:` line's model, and the filled prompt. Find the account's environment at run time; never write its id or a trigger's id in the kit or the project.
3. Then, right after `create`, `update` the routine with `clear_mcp_connections: true`: creating one attaches the account's connectors even when the request asks for none.

If routines can't take an effort, tell the owner so when you dispatch them.

## Watch

- Watch the runner's `.agent-batch/batch-<batch>/events.jsonl` with the `Monitor` tool, and the routines' runs with `RemoteTrigger`'s `list_runs`.
- A `Monitor` watch lasts 30 minutes at most: re-arm it until the batch ends, lanes and cloud.

## Bring a cloud branch back

When a cloud run ends:

1. Read its answer with `RemoteTrigger`'s `list_runs` and `get_run_log`: the branch, its head SHA, the PR's title and body, and the environment's problems.
2. `git fetch origin <branch>`, then `git worktree add .agent-batch/worktrees/ship-<n> -b <branch> origin/<branch>`, and `make setup` in it.
3. Write the PR body to a file outside the repository and, in the worktree, run `agent-batch ship <n> --title "<title>" --body-file <file>`, with `--model` and `--effort` when `Model:` names them. That's a fresh local review, and a PR that merges by its risk.
4. If the review asks for changes, the branch goes back to the cloud or to the owner; tell the owner which, and why.

A run that failed, or ended without pushing its branch, is a failed cloud run (see Notify).

## Notify

Send the owner's phone a notification with `PushNotification` only when:

- an issue is blocked: `issue_finished` with `blocked`;
- the budget is reached: `issue_set_aside` with "the batch stopped";
- a cloud run fails;
- the whole batch ended, lanes and cloud.

Never notify for each PR. Each notification says what happened and what the owner can do, in one or two sentences.

## The cloud's results

Comment "Cloud" on the tracking issue once the cloud issues have all shipped or failed: each cloud issue's branch, PR, minutes and outcome, since the runner's summary doesn't know them.

## Resume

When the owner asks to continue a batch, don't start it over:

- Start the runner again if its lanes didn't finish; it picks up the branches that exist.
- Find the batch's routines that already ran with `RemoteTrigger`'s `list` and `list_runs`, and bring back, as above, those whose branch has no PR yet: `gh pr list --head <branch> --state all` prints nothing.
- Send to the cloud only the `Cloud:` issues that have no routine yet.

## Next step

When the whole batch ended, end with one next step: ask the owner whether to accept the batch now, with the `accept-batch` skill.
