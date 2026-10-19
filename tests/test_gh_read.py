"""`agent-batch gh-read` runs only `gh`'s reads of pull requests and the API (#72)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from agent_batch import cli

# Writes down the arguments it got, one per line, prints to both streams and exits as told.
FAKE_GH = """#!/bin/sh
printf '%s\\n' "$@" > "$FAKE_GH_ARGS"
printf 'what gh printed\\n'
printf 'what gh warned\\n' >&2
exit "$FAKE_GH_CODE"
"""
PR_READS = [
    ("pr", "view", "72", "--json", "title,body"),
    ("pr", "list", "--state", "open"),
    ("pr", "diff", "72"),
    ("pr", "checks", "72"),
]
OTHER_COMMANDS = [
    ("pr", "merge", "72", "--squash"),
    ("pr", "edit", "72", "--add-label", "ready"),
    ("pr", "comment", "72", "--body", "hi"),
    ("pr", "close", "72"),
    ("pr", "--repo", "owner/project", "merge", "72"),
    ("issue", "close", "72"),
    ("repo", "delete", "owner/project", "--yes"),
    ("label", "delete", "ready"),
]
ISSUES = "repos/owner/project/issues"
# Each refused api call, the argument it's refused for, and a word of the reason it gives.
API_WRITES = [
    (("api", "-X", "POST", ISSUES), "-X", "GET"),
    (("api", "-X", "GET", ISSUES), "-X", "GET"),
    (("api", "-XDELETE", "repos/owner/project/git/refs/heads/x"), "-XDELETE", "GET"),
    (("api", "-iX", "POST", ISSUES), "-iX", "GET"),
    (("api", "--method", "PATCH", "repos/owner/project"), "--method", "GET"),
    (("api", "--method=PUT", "repos/owner/project/pulls/72/merge"), "--method=PUT", "GET"),
    (("api", ISSUES, "-f", "title=x"), "-f", "body"),
    (("api", ISSUES, "-ftitle=x"), "-ftitle=x", "body"),
    (("api", ISSUES, "-F", "title=x"), "-F", "body"),
    (("api", ISSUES, "--field", "title=x"), "--field", "body"),
    (("api", ISSUES, "--raw-field=title=x"), "--raw-field=title=x", "body"),
    (("api", ISSUES, "--input", "body.json"), "--input", "body"),
    (("api", "graphql"), "graphql", "REST"),
    (("api", "/graphql"), "/graphql", "REST"),
    (("api", "https://api.github.com/graphql"), "https://api.github.com/graphql", "REST"),
]


@dataclass(frozen=True)
class FakeGh:
    args_file: Path

    def called_with(self) -> list[str] | None:
        """The arguments gh ran with, or None when it never ran."""
        if not self.args_file.exists():
            return None
        return self.args_file.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeGh:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "gh"
    fake.write_text(FAKE_GH)
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setenv("FAKE_GH_ARGS", str(tmp_path / "gh-args"))
    monkeypatch.setenv("FAKE_GH_CODE", "0")
    monkeypatch.chdir(tmp_path)
    return FakeGh(tmp_path / "gh-args")


def gh_read(*args: str) -> int:
    """`agent-batch gh-read`'s exit code, also when argparse exits on a usage error."""
    try:
        return cli.main(["gh-read", *args])
    except SystemExit as exited:
        return int(exited.code or 0)


@pytest.mark.parametrize("args", PR_READS, ids=" ".join)
def test_gh_read_runs_each_pull_request_read_and_passes_its_output_through(
    gh: FakeGh, capsys: pytest.CaptureFixture[str], args: tuple[str, ...]
) -> None:
    code = gh_read(*args)

    out, err = capsys.readouterr()
    assert code == 0
    assert gh.called_with() == list(args)
    assert out == "what gh printed\n"
    assert "what gh warned" in err


def test_gh_read_runs_an_api_call_as_a_get_and_passes_its_output_through(
    gh: FakeGh, capsys: pytest.CaptureFixture[str]
) -> None:
    code = gh_read("api", "repos/owner/project/milestones", "--jq", ".[].title")

    out, err = capsys.readouterr()
    assert code == 0
    called = gh.called_with()
    assert called is not None
    assert called[0] == "api"
    assert called[called.index("--method") + 1] == "GET"
    assert [arg for arg in called if arg not in ("--method", "GET")] == [
        "api", "repos/owner/project/milestones", "--jq", ".[].title",
    ]  # fmt: skip
    assert out == "what gh printed\n"
    assert "what gh warned" in err


def test_gh_read_passes_through_the_exit_code_and_error_of_a_read_that_fails(
    gh: FakeGh, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_GH_CODE", "1")

    code = gh_read("pr", "view", "999")

    assert code == 1
    assert gh.called_with() == ["pr", "view", "999"]
    assert "what gh warned" in capsys.readouterr().err


@pytest.mark.parametrize("args", OTHER_COMMANDS, ids=" ".join)
def test_gh_read_refuses_any_other_gh_command_saying_why_without_calling_gh(
    gh: FakeGh, capsys: pytest.CaptureFixture[str], args: tuple[str, ...]
) -> None:
    code = gh_read(*args)

    err = capsys.readouterr().err
    assert code != 0
    assert gh.called_with() is None
    assert f"gh-read refuses `gh {args[0]} {args[1]}`" in err
    assert "pr view" in err


@pytest.mark.parametrize(
    ("args", "refused", "reason"), API_WRITES, ids=[" ".join(args) for args, _, _ in API_WRITES]
)
def test_gh_read_refuses_a_method_a_body_a_field_or_graphql_saying_why_without_calling_gh(
    gh: FakeGh,
    capsys: pytest.CaptureFixture[str],
    args: tuple[str, ...],
    refused: str,
    reason: str,
) -> None:
    code = gh_read(*args)

    err = capsys.readouterr().err
    assert code != 0
    assert gh.called_with() is None
    assert f"gh-read refuses `{refused}`" in err
    assert reason in err
