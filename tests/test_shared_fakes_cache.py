"""`shared_fakes` keeps its fakes in pytest's cache, and nothing half written there (#239)."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import conftest


class Cache:
    """pytest's cache, as `shared_fakes` uses it: a folder per name, under one of its own."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def mkdir(self, name: str) -> Path:
        folder = self.root / name
        folder.mkdir(parents=True, exist_ok=True)
        return folder


def shared_fakes(config: object, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Calls the fixture's function with the arguments it names."""
    fixture: Any = conftest.shared_fakes
    function = fixture.__wrapped__
    given = {"request": SimpleNamespace(config=config), "tmp_path_factory": tmp_path_factory}
    names = inspect.signature(function).parameters
    path: Path = function(**{name: given[name] for name in names})
    return path


def test_shared_fakes_uses_pytests_cache_with_no_fallback_for_a_missing_one(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    with pytest.raises(AttributeError):
        shared_fakes(SimpleNamespace(), tmp_path_factory)


def test_a_first_session_whose_write_of_the_fakes_fails_leaves_nothing_in_the_cache(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fails(shared: Path, fakes: dict[str, str]) -> None:
        (shared / next(iter(fakes))).write_text("half")
        raise OSError("No space left on device")

    monkeypatch.setattr(conftest, "_shared_fakes", fails)
    cache = Cache(tmp_path / "cache")

    with pytest.raises(OSError, match="No space left"):
        shared_fakes(SimpleNamespace(cache=cache), tmp_path_factory)

    assert list(cache.mkdir("fakes").iterdir()) == []
