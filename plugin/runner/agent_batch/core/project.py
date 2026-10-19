"""Whether a project enables agent-kit in its own settings (SPEC §13)."""

from __future__ import annotations

import json

# The project's settings files, as the hooks read them in `agent_hooks.repo.enabled_here`: the
# runner and the hooks don't depend on each other, so each has its own copy.
SETTINGS = (".claude/settings.json", ".claude/settings.local.json")
PLUGIN = "agent-kit@"


def enables_agent_kit(text: str) -> bool:
    """Whether one settings file's text turns the plugin on; text that isn't JSON doesn't."""
    try:
        settings = json.loads(text)
    except json.JSONDecodeError:
        return False
    plugins = settings.get("enabledPlugins") if isinstance(settings, dict) else None
    return isinstance(plugins, dict) and any(
        key.startswith(PLUGIN) and value is True for key, value in plugins.items()
    )
