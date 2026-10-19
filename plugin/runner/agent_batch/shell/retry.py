"""A call to GitHub, tried again while GitHub answers with a server error (#195)."""

from __future__ import annotations

import time
from collections.abc import Callable

from agent_batch.core.server_errors import is_server_error
from agent_batch.shell.proc import CommandError

TRIES = 3


def retried[T](call: Callable[[], T], wait: float) -> T:
    """The call's result, after up to `TRIES` tries `wait` seconds apart.

    Only a server error is tried again: another failure, such as a rejected push, would fail the
    same way.
    """
    failure: CommandError | None = None
    for attempt in range(TRIES):
        if attempt:
            time.sleep(wait)
        try:
            return call()
        except CommandError as error:
            if not is_server_error(str(error)):
                raise
            failure = error
    raise CommandError(
        f"The call failed after {TRIES} tries, each with a GitHub server error; the last one: "
        f"{failure}"
    ) from failure
