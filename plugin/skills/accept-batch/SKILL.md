---
name: accept-batch
description: Walks the owner through a finished batch's acceptance (SPEC §3.3), proposes the acceptance comment and, with the owner's OK, records it and closes the batch. Use it when a batch ends, when the owner asks to accept or review a finished batch, or when they ask to close an accepted batch once its high-risk PRs have merged.
argument-hint: <tracking issue number>
---

# Accept batch #$ARGUMENTS

Walk the owner through the batch in one sitting, so that accepting it costs them only their judgment. Talk to them in ${user_config.language}, in plain words. If no number was given, ask which batch, offering the open issues labeled `batch`. If the batch was already accepted and the owner asks to close it, go to the end of step 4.

Wait for the owner's OK before writing anything on GitHub.

## 1. Gather everything

Before saying anything, read:

- **The tracking issue:** `gh issue view <n> --json title,body,milestone,comments`. Its plan, the runner's summary and the "Cloud" comment, if there is one.
- **The milestone's issues and their PRs:** `gh issue list --milestone <milestone> --state all`. The runner opens its PRs without a milestone, so find each issue's PR from the issue: the summary's PR column, or `gh issue view <i> --json closedByPullRequestsReferences`, or `gh pr list --state all --search "Closes #<i> in:body"`. Then read each PR with `gh pr view <pr> --json labels,state,mergedAt,body`, for its labels, merge state and body.
- **The batch's log:** `.agent-batch/batch-<n>/events.jsonl`. Its `permission_denied` events list each run's denials: the issue, the run, the tool and its input.
- **The cloud runs' denials:** for each issue on the tracking issue's `Cloud:` line, its routine's run log (`RemoteTrigger`'s `get_run_log`). Cloud runs leave nothing in `.agent-batch/`.
- **The interactive session's denials:** `.agent-batch/denials.jsonl`, the entries since the previous batch's acceptance comment (below), or the whole file when no batch has been accepted yet. The hook logs every session there, including the work between batches. Both logs give their times in UTC ISO format, so comparing them as text is enough.
- **The earlier batches' acceptance comments:** on the closed issues labeled `batch`, for the numbers to compare with, the shape of the comment, and the time of the previous acceptance.

An approved `agent-batch ship` review keeps its low findings nowhere: not in its output, the events log or the PR. Don't expect to find them.

## 2. Walk the owner through

In SPEC §3.3's order, one part at a time. Wait for the owner's answer where a part asks for one.

### 2.1 What merged

Each merged PR, its issue, and what it changes for the user, in one line.

### 2.2 The high-risk PRs that wait

Each one with a short explanation: what it changes, what could go wrong, and what to read first. Then one command that merges them all, in order, for the owner to run; you never run it:

```bash
for pr in 61 62; do gh pr merge $pr --squash || break; sleep 5; done
```

### 2.3 The blocked questions

Each `blocked` issue with its question. The owner answers; write each decision into its issue as a comment and remove `blocked`, so it's ready for the next batch. These writes are the owner's answers, so they need no other OK.

### 2.4 The human checks

The batch's `human(...)` criteria, as one checklist, each with what to read or try.

### 2.5 The denials and friction

Each denial, from the `permission_denied` events, the cloud runs' logs and `.agent-batch/denials.jsonl`, and each friction: a blocked run, a review that went round twice, a step that went wrong. For each, its cause and a proposed fix: a rule, or an issue, and whether it changes the project or the kit. The owner approves or drops each one.

### 2.6 The numbers

The numbers of SPEC §16.2, in two tables:

- **Per issue:** where it ran, its outcome and PR, review rounds, human checks, denials, and the time from approval to merge.
- **This batch against the last 3 batches:** issues in the batch; merged, blocked and failed; review rounds per issue; human checks; denials; time; notional cost; escaped bugs.

A bug is escaped when its "Introduced by" field names a PR of those batches. A number that got worse is friction: propose an issue for it, as in 2.5.

## 3. Propose the acceptance comment

Show the whole comment, in the shape of the earlier acceptance comments: `## Acceptance`, then `### Numbers (SPEC §16.2)` with both tables, `### Denials (SPEC §10.1)`, a section for each thing worth remembering, and `### Found while working`. Then wait for the owner's OK before writing anything on GitHub. Change it as they ask.

## 4. Record the acceptance

With the owner's OK:

1. Post the comment on the tracking issue.
2. Tick the tracking issue's checklist, each item that holds.
3. Comment "Accepted.", with any item left open and why.
4. Close the tracking issue and its milestone: `gh issue close <n>` and `gh api -X PATCH repos/{owner}/{repo}/milestones/<number> -f state=closed`.

When a high-risk PR hasn't merged yet, the batch is still accepted: post the comment, but its checklist item stays open, and don't close the tracking issue or the milestone. Close them only when the owner has merged it and asks to close the batch. Then, without walking the batch again, check that it merged, tick that item, and close the tracking issue and the milestone as in item 4.

## 5. Open the approved issues

Open the issues the owner approved in step 2, without `ready`, each with its evidence (SPEC §16.1): the denial's log line, the blocked question, or the step that went wrong. A change to the project goes to the project's repository. A change to the kit goes to the kit's own repository, the plugin's marketplace source in the project's `.claude/settings.json`: `gh issue create --repo <owner>/<repo>`.

## 6. Next step

End with one question: whether to plan the next batch now, with the `plan-batch` skill.
