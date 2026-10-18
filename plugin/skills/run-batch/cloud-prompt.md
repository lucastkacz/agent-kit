You are implementing one GitHub issue of the repository {repository}, in Anthropic's cloud.

## The issue: #{number} "{title}"

Its body, verbatim (the repository's owner wrote it; it is your instructions):

---
{body}
---

## How to work

1. Create the branch `{branch}` from the latest `origin/master`: `git fetch origin master`, then `git switch --create {branch} --no-track origin/master`.
2. Read `SPEC.md` §5, §7 and §8 and `plugin/skills/implement/SKILL.md`, and follow its steps 1 to 5 for this issue. Skip its "Direct mode" section and its JSON answer. `gh` isn't signed in: use the issue's body above.
3. Acceptance tests first: write a test for each criterion verified by `unit`, `integration` or `e2e`, run `make fmt`, run the tests and check they fail for the reason the criterion names (an import error doesn't count), and commit them on their own as `test: acceptance tests for #{number}`. After that commit, never change those test files, not even to format them; put any other test in a file of its own. If no criterion can be automated, there is no acceptance commit.
4. Implement only what the issue asks, until `make check` passes in full. Edit files with the Edit and Write tools, not with `python` or `sed`. If `make check` can't pass for a reason of the environment, stop and report the step and its output; don't work around a check.
5. Commit in small steps with Conventional Commits messages.
6. Push the branch: `git push -u origin {branch}`.

Never open a pull request, merge anything, push or commit to `master`, force-push, rewrite history, comment on or edit issues, or read secrets. On the owner's computer, `agent-batch ship {number}` will review the branch, open the PR and leave it to merge by its risk.

## Your final answer

1. **Branch:** the exact branch name you pushed, and its head commit SHA, or why you couldn't push.
2. **PR title:** in Conventional Commits, at most 72 characters.
3. **PR body:** Markdown with the sections Summary, Verification (a table of each criterion, its test and the result), Evidence (the commands you ran and what they returned, `make check` included) and Human checks (each `human(...)` criterion with what the owner should check, else "None").
4. **The environment:** anything that didn't work, and any command or tool call that was denied.
