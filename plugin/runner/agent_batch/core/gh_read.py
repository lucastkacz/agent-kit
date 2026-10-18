"""`agent-batch gh-read`: the reviewer's read-only way into pull requests and GitHub's API (#72).

The reviewer runs on the owner's admin token, so `gh pr` and `gh api` stay denied to it: through
them it could merge, label, comment or delete. This lets through only their reads, and refuses
anything else before `gh` runs.
"""

from __future__ import annotations

from collections.abc import Sequence

PR_READS = ("view", "list", "diff", "checks")
READS = "it runs only `pr view`, `pr list`, `pr diff`, `pr checks` and GET `api` calls"
GET_ONLY = "api calls are GET only, so gh-read sets the method itself"
NO_BODY = "api calls send no body or fields, which would make them a POST"
REST_ONLY = "GraphQL can run mutations, so gh-read calls only the REST API"
# The `gh api` flags, long and short, that would choose the method or send a body.
LONG_FLAGS = {"--method": GET_ONLY, "--input": NO_BODY, "--field": NO_BODY, "--raw-field": NO_BODY}
SHORT_FLAGS = {"X": GET_ONLY, "f": NO_BODY, "F": NO_BODY}


class Refused(Exception):
    """A gh-read call that isn't one of its reads, or that could write."""


def command(args: Sequence[str]) -> list[str]:
    """The `gh` command line for a read, or `Refused` saying why the call isn't one."""
    match list(args):
        case ["pr", read, *rest] if read in PR_READS:
            return ["gh", "pr", read, *rest]
        case ["api", *rest]:
            for arg in rest:
                _check_api_arg(arg)
            return ["gh", "api", "--method", "GET", *rest]
    called = " ".join(["gh", *args[:2]])
    raise Refused(f"gh-read refuses `{called}`: {READS}")


def _check_api_arg(arg: str) -> None:
    """Refuses an argument that chooses the method, sends a body or calls GraphQL.

    Every argument is checked, values too: a false alarm only costs a retry, a miss a write.
    """
    reason = _api_refusal(arg)
    if reason is not None:
        raise Refused(f"gh-read refuses `{arg}`: {reason}")


def _api_refusal(arg: str) -> str | None:
    if arg.startswith("--"):
        return LONG_FLAGS.get(arg.partition("=")[0])
    if arg.startswith("-"):
        # gh reads `-iXPOST` as `-i -X POST`, so a short flag counts anywhere in the cluster.
        return next((SHORT_FLAGS[flag] for flag in arg[1:] if flag in SHORT_FLAGS), None)
    path = arg.partition("?")[0].rstrip("/").lower()
    return REST_ONLY if path == "graphql" or path.endswith("/graphql") else None
