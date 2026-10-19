"""Stands in for `claude -p` in tests, following a scripted scenario.

The scenario maps a kind of run (implement, review, fix, resolve) and an issue number to the steps
that its calls take in order. A step can answer with an `output`, fail with an `error`, print `raw`
text or `sleep`; when the steps run out, the run succeeds with a default answer. A step can also say
the computer `slept` that many seconds: the test's wall clock moves on by them.

Asked for `--output-format stream-json`, it prints one message per line, as the real one does: its
start, an assistant message for each of the step's `tools`, then its answer. With `snapshot`, it
waits after each tool use until the runner's status files change, and keeps a copy of them.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

Step = dict[str, Any]

KINDS = (
    ("implement", re.compile(r"^/agent-kit:implement (\d+)")),
    ("review", re.compile(r"^/agent-kit:review (\d+)")),
    ("fix", re.compile(r"^The reviewer asked for changes on #(\d+)")),
    ("resolve", re.compile(r"^Merging .* into the branch of #(\d+)")),
)
DONE = {"status": "done", "title": "", "pr_body": "", "message": "", "found": []}
DENIAL = {
    "tool_name": "Bash",
    "tool_use_id": "toolu_fake",
    "tool_input": {"command": "git push origin HEAD"},
}
# How long a `snapshot` waits for the runner to show a tool use before it keeps what it finds.
SNAPSHOT_WAIT = 5.0


def default_output(kind: str, number: int) -> dict[str, Any]:
    if kind == "review":
        return {"verdict": "approved", "findings": []}
    if kind == "resolve":
        return {"status": "resolved", "message": ""}
    return {**DONE, "title": f"feat: deliver #{number}", "pr_body": f"Delivers #{number}."}


def classify(prompt: str) -> tuple[str, int]:
    for kind, pattern in KINDS:
        match = pattern.match(prompt)
        if match:
            return kind, int(match.group(1))
    raise SystemExit(f"the fake claude doesn't know this prompt: {prompt!r}")


def next_step(kind: str, number: int) -> tuple[Step, int]:
    """The scripted step for this call, and how many calls of its kind came before it."""
    scenario = json.loads(Path(os.environ["FAKE_CLAUDE_SCENARIO"]).read_text())
    counts_path = Path(os.environ["FAKE_CLAUDE_LOG"]).with_suffix(".counts")
    key = f"{kind}-{number}"
    with counts_path.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        counts = json.loads(counts_path.read_text()) if counts_path.exists() else {}
        index = counts.get(key, 0)
        counts[key] = index + 1
        counts_path.write_text(json.dumps(counts))
    steps: list[Step] = scenario.get(kind, {}).get(str(number), [])
    return (steps[index] if index < len(steps) else {}), index


def record(argv: list[str], kind: str, number: int) -> None:
    entry = {
        "kind": kind,
        "number": number,
        "argv": argv,
        "cwd": str(Path.cwd()),
        "api_key": "ANTHROPIC_API_KEY" in os.environ,
        "auth_token": "ANTHROPIC_AUTH_TOKEN" in os.environ,
        "claudecode": "CLAUDECODE" in os.environ,
        "screen": os.environ.get("AGENT_BATCH_SCREEN"),
    }
    log = Path(os.environ["FAKE_CLAUDE_LOG"])
    with log.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with log.open("a") as out:
            out.write(json.dumps(entry) + "\n")


def sleep_computer(seconds: float) -> None:
    """Adds `seconds` to the sleep the test's wall clock counts (`World.slept`)."""
    slept = Path(os.environ["FAKE_SLEPT"])
    with slept.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        before = float(slept.read_text()) if slept.exists() else 0.0
        staged = slept.with_suffix(".tmp")
        staged.write_text(str(before + seconds))
        # The runner reads the file while this runs; a replace never shows it half written.
        staged.replace(slept)


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True)


def commit_work(number: int, files: list[str] | None) -> None:
    for name in files or [f"work_{number}.txt"]:
        path = Path.cwd() / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as out:
            out.write(f"work on #{number}\n")
    git("add", "-A")
    git("commit", "--quiet", "-m", f"feat: work on #{number}")


def resolve_conflicts() -> None:
    conflicted = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    for name in conflicted:
        (Path.cwd() / name).write_text("resolved\n")
    git("add", "-A")
    git("commit", "--quiet", "--no-edit")


def result_json(kind: str, number: int, step: Step, count: int) -> dict[str, Any]:
    """What the fake prints, in the shape `tests/contract/recorded/claude-*.json` recorded.

    A step's `denials` is either how many copies of `DENIAL` it had, or the list of its denials.
    """
    denials = step.get("denials", 0)
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "",
        "session_id": f"session-{kind}-{number}-{count}",
        "total_cost_usd": 0.01,
        "permission_denials": denials if isinstance(denials, list) else [DENIAL] * int(denials),
        "structured_output": step.get("output") or default_output(kind, number),
    }


def tool_message(tool: Step) -> dict[str, Any]:
    """An assistant message with one tool use, in the shape `claude-stream.json` recorded.

    A relative `file_path` is taken from the run's folder, since the real tools take absolute ones.
    """
    tool_input = dict(tool.get("input", {}))
    path = tool_input.get("file_path")
    if isinstance(path, str) and not Path(path).is_absolute():
        tool_input["file_path"] = str(Path.cwd() / path)
    block = {"type": "tool_use", "id": "toolu_fake", "name": tool["name"], "input": tool_input}
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [block]},
        "parent_tool_use_id": None,
        "session_id": "session-fake",
    }


def emit(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def statuses() -> dict[str, str]:
    """The runner's status files, by their path in its state folder."""
    state = Path(os.environ["FAKE_STATE_DIR"])
    return {
        str(path.relative_to(state)): path.read_text()
        for path in sorted(state.glob("*/status.json"))
    }


def snapshot(kind: str, number: int, before: dict[str, str]) -> None:
    """Keeps the status files once the runner changed them, as `World.status_snapshots` reads."""
    deadline = time.monotonic() + SNAPSHOT_WAIT
    seen = statuses()
    while seen == before and time.monotonic() < deadline:
        time.sleep(0.01)
        seen = statuses()
    log = Path(os.environ["FAKE_CLAUDE_LOG"]).with_suffix(".status")
    with log.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with log.open("a") as out:
            out.write(json.dumps({"kind": kind, "number": number, "status": seen}) + "\n")


def stream_tools(kind: str, number: int, step: Step, count: int) -> None:
    emit({"type": "system", "subtype": "init", "session_id": f"session-{kind}-{number}-{count}"})
    for tool in step.get("tools", []):
        before = statuses()
        emit(tool_message(tool))
        if step.get("snapshot"):
            snapshot(kind, number, before)


def answer(kind: str, number: int, step: Step, count: int) -> int:
    result = result_json(kind, number, step, count)
    output = result["structured_output"]
    if kind in ("implement", "fix") and output.get("status") == "done":
        commit_work(number, step.get("files"))
    if kind == "resolve" and output.get("status") == "resolved":
        resolve_conflicts()
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


def streaming(argv: list[str]) -> bool:
    return "--output-format" in argv and argv[argv.index("--output-format") + 1] == "stream-json"


def main(argv: list[str]) -> int:
    kind, number = classify(argv[argv.index("-p") + 1])
    step, count = next_step(kind, number)
    record(argv, kind, number)
    if streaming(argv):
        stream_tools(kind, number, step, count)
    if "slept" in step:
        sleep_computer(float(step["slept"]))
    if "sleep" in step:
        time.sleep(float(step["sleep"]))
    if "raw" in step:
        sys.stdout.write(str(step["raw"]))
        return int(step.get("code", 0))
    if "error" in step:
        error = {"type": "result", "is_error": True, "result": step["error"]}
        sys.stdout.write(json.dumps(error) + "\n")
        return 1
    return answer(kind, number, step, count)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
