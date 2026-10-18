"""Reading a shell command the way the shell will run it: which git commands, in which folder.

Quoted text and heredoc bodies are text, not commands, and `cd` and `git -C` change the folder.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

PUNCTUATION = ";&|\n"
# A heredoc's opening (`<<EOF`, `<<-'EOF'`), but not a here-string (`<<<`).
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# git's options that come before the subcommand and take the next word as their value.
VALUED_OPTIONS = frozenset({"-c", "--git-dir", "--work-tree", "--namespace"})


@dataclass(frozen=True)
class GitCall:
    directory: Path
    subcommand: str
    args: tuple[str, ...]


def git_calls(command: str, cwd: Path) -> list[GitCall]:
    """The git commands in a shell command, each with the folder it runs in."""
    try:
        commands = simple_commands(without_heredocs(command))
    except ValueError:
        # The shell can't parse it either, so it runs nothing.
        return []
    calls: list[GitCall] = []
    directory = cwd
    for words in map(_without_assignments, commands):
        if words[:1] == ["cd"] and len(words[1:]) == 1:
            directory = _resolve(directory, words[1])
        elif words[:1] == ["git"]:
            call = _git_call(words[1:], directory)
            if call is not None:
                calls.append(call)
    return calls


def without_heredocs(text: str) -> str:
    kept: list[str] = []
    ending: tuple[str, bool] | None = None
    for line in text.split("\n"):
        if ending is not None:
            delimiter, tabs = ending
            if (line.lstrip("\t") if tabs else line) == delimiter:
                ending = None
            continue
        kept.append(line)
        match = HEREDOC.search(line)
        if match is not None:
            ending = (match.group(3), match.group(1) == "-")
    return "\n".join(kept)


def simple_commands(text: str) -> list[list[str]]:
    """The words of each command between `;`, `&&`, `||`, `|`, `&` and new lines."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    commands: list[list[str]] = [[]]
    for token in lexer:
        if token and set(token) <= set(PUNCTUATION):
            commands.append([])
        else:
            commands[-1].append(token)
    return [words for words in commands if words]


def _without_assignments(words: list[str]) -> list[str]:
    index = 0
    while index < len(words) and ASSIGNMENT.match(words[index]):
        index += 1
    return words[index:]


def _git_call(args: list[str], directory: Path) -> GitCall | None:
    index = 0
    while index < len(args) and args[index].startswith("-"):
        if args[index] == "-C" and index + 1 < len(args):
            directory = _resolve(directory, args[index + 1])
            index += 2
        elif args[index] in VALUED_OPTIONS:
            index += 2
        else:
            index += 1
    if index >= len(args):
        return None
    return GitCall(directory, args[index], tuple(args[index + 1 :]))


def _resolve(directory: Path, target: str) -> Path:
    path = Path(target).expanduser()
    return Path(os.path.normpath(path if path.is_absolute() else directory / path))
