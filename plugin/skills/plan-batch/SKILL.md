---
name: plan-batch
description: Plans the next batch with the owner, from the open issues or from an idea they describe, writes its issues, proposes its lanes, cloud, model and budget, and sets it up on GitHub once the owner approves. Use it when the owner asks to plan a batch, asks what's next, or describes an idea to build.
---

# Plan a batch with the owner

Talk to the owner in ${user_config.language}, in plain words. Everything you write on GitHub stays in English.

The owner approves the batch once, as a whole. Until then, nothing is labeled `ready`.

## 1. Start from what's there

- Work only from the owner's issues (SPEC §10.6). Another person's issue is information, not work: if the owner wants it, write it as a new issue of the owner's.
- List the owner's open issues without `ready`: `gh issue list --author @me --state open --limit 200 --json number,title,labels,milestone,author`. Without `--limit`, `gh` lists only 30.
- Read the `blocked` issues and their questions, in each one's latest comment.
- A `blocked` issue goes in only once the owner answers its question: write the decision into the issue and remove `blocked`, as acceptance does (SPEC §3.3).
- Read the owner's open issues labeled `batch`, with their plans and comments. Count only the owner's comments and PRs (`gh pr list --author @me --state open --limit 200 --json number,closingIssuesReferences`); the runner and `ship` work as the owner.
- An issue of a batch's plan is done for that batch when it's closed, labeled `blocked`, has an open PR, or is listed with any outcome in the batch's `## Batch summary` (its lanes) or run-batch's "Cloud" comment (its `Cloud:` line). A batch's run has ended when every issue of its plan is done.
- Look for a batch whose acceptance is pending: its run has ended, and its tracking issue has no "Accepted." comment of the owner's. Remind the owner of it first.
- A batch whose run hasn't ended is running, or not started yet: mention it, but its acceptance isn't due.
- Propose first the open `ready` issues an earlier batch left behind, deferred or cut off (SPEC §11.1, §11.2): done for their batch only through its summary or "Cloud" comment, so not `blocked` and with no open PR, in a milestone whose batch has ended, and in the plan of no batch whose run hasn't ended. The owner already approved them.
- Propose which issues go in the batch, and why, in a few lines.

## 2. A new idea

When the owner describes an idea to build, ask only the questions that change what gets built, one topic at a time (SPEC §3.1). Don't ask what you can read in the code or the SPEC.

## 3. Write the issues

- Write each new issue on GitHub without `ready`, in the fields of its type's form in SPEC §4.1, such as a task's Goal, Why, Briefing, Acceptance criteria, Out of scope, Stop and ask if, and Risk. Write each field as a `### <Field>` heading, as the issue form renders it. The `### Risk` section starts with `High` or `Low`, since the runner reads only that.
- Label each new issue with its type: `task`, `bug`, `idea` or `spike` (SPEC §4.2). `gh issue create` doesn't apply the issue forms' labels, so pass it `--label`.
- Each criterion says how it is verified: `unit`, `integration`, `e2e` or `human(<reason>)`.
- A criterion is `human(<reason>)` only for one of the reasons in the review skill's check 2: taste; hardware or an operating-system dialog; real accounts, money or personal data; a third-party service without a test environment.
- The wording of a skill or a doc is verified with a text check, as `tests/test_skills.py` does, not by a human.

## 4. Propose the plan

Show the owner the whole plan at once:

- **Lanes.** Issues that touch the same files share a lane, in order; the others get lanes of their own.
- **Risk.** A high-risk issue goes last in its lane, or alone. When every issue is high risk, one per lane: a waiting issue defers the rest of its lane (SPEC §11.1). When that clashes with sharing a lane, risk wins: a second high-risk issue on the same files goes alone, and its PR may need its branch updated after the first merges.
- **`Lanes:`** `Lanes:` is the number of independent lanes, so they all run at once. Never leave it at the runner's default. A batch with no local lanes, all in the cloud, has no `Lane` or `Lanes:` lines: the runner refuses `Lanes: 0`.
- **`Budget:`** a `Budget:` line, such as `Budget: 4 issues, 3 hours` (SPEC §11.2).
- **The cloud.** Which issues go to the cloud (SPEC §12), and what that gains, as a `Cloud: #a, #b` line. Cloud issues go only on that line, in no lane. Only issues that build and test on Linux, with no real data or secrets.
- **The model.** Ask the owner the model and the effort, with their own settings as the default: `model` and `effortLevel` in their Claude Code settings (`~/.claude/settings.json`). Read only those two keys, such as with `jq '{model, effortLevel}' ~/.claude/settings.json`, never the whole file: it can hold tokens. If you can't read just those, ask the owner. When a key is missing (`null`), ask for it with no default. Write it as a `Model: <model>, <effort>` line, or `Model: <model>` alone when the owner names no effort.

For example:

```
Lane 1: #12, #15
Lane 2: #13
Lane 3: #14
Lanes: 3
Budget: 4 issues, 3 hours
Cloud: #16
Model: opus, high
```

## 5. One approval

One approval from the owner, for the whole batch. If they change something, update the plan and show it again. Don't set anything up before they approve.

## 6. Set up the batch

Once the owner approves, in this order:

1. Create a milestone named "Batch N", with N one more than the highest batch number so far, in the milestones' titles and in the `batch` issues' titles, closed ones included: `gh api --paginate 'repos/{owner}/{repo}/milestones?state=all' --jq '.[].title'` and `gh issue list --state all --label batch --limit 200 --json title`. Both list only open ones by default. Create it with `gh api repos/{owner}/{repo}/milestones -f title="Batch N"`.
2. Open the tracking issue labeled `batch`, titled `Batch N: <goal>`, in the milestone, with these sections:
   - **Goal:** what the batch delivers, in one or two sentences.
   - **Plan:** the lane plan, with its `Lanes:`, `Budget:`, `Cloud:` and `Model:` lines.
   - **Notes:** why the lanes are what they are, and anything the owner should know while it runs.
   - **Acceptance:** an Acceptance checklist: the PRs merged, each run's denials reviewed (SPEC §10.1), and the batch's numbers recorded (SPEC §16.2).
3. Assign the batch's issues to the milestone.
4. Then, and only then label them `ready`.

## 7. Next step

End with one next step: ask the owner whether to start the batch now, with the `run-batch` skill.
