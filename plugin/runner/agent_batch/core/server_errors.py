"""Whether a failed call to GitHub was GitHub's own fault, and so worth trying again (#195)."""

from __future__ import annotations

import re

# What git and gh print when GitHub answers with an HTTP 5xx, or GraphQL fails on its side.
SERVER_ERROR = re.compile(
    r"HTTP 5\d\d\b"
    r"|returned error: 5\d\d\b"
    r"|Internal Server Error|Bad Gateway|Service Unavailable|Gateway Time-?out"
    r"|GraphQL: Something went wrong",
    re.IGNORECASE,
)


def is_server_error(message: str) -> bool:
    return SERVER_ERROR.search(message) is not None
