"""An edit to a markdown config file reaches the agent (DX-2, CFG-6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.src.agent.config import resolution
from agent.src.agent.config.parser import parse_frontmatter

PROMPT = """---
name: orchestrator
description: the shipped one
---

The shipped body.
"""

EDITED = """---
name: orchestrator
description: the edited one
---

The edited body.
"""


class _Overlay:
    """The shape `use_overlay` expects: a generation and `current`."""

    generation = 1

    def __init__(self, entries: dict[str, str]):
        self._entries = entries

    def current(self, key: str) -> str | None:
        return self._entries.get(key)


@pytest.fixture
def on_disk(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr("agent.src.agent.config.paths.config_root", lambda: tmp_path)
    path = tmp_path / "PROMPT.md"
    path.write_text(PROMPT)
    return path


@pytest.fixture(autouse=True)
def no_overlay_afterwards():
    yield
    resolution.use_overlay(None)


class TestWithNoOverlay:
    def test_it_is_the_file(self, on_disk):
        assert parse_frontmatter(on_disk)["body"] == "The shipped body."


class TestWithAnEdit:
    def test_the_body_is_the_edited_one(self, on_disk):
        key = resolution.overlay_key(on_disk)
        assert key is not None, "the overlay cannot key this path"
        resolution.use_overlay(_Overlay({key: EDITED}))
        assert parse_frontmatter(on_disk)["body"] == "The edited body."

    def test_and_so_is_the_frontmatter(self, on_disk):
        key = resolution.overlay_key(on_disk)
        resolution.use_overlay(_Overlay({key: EDITED}))
        assert parse_frontmatter(on_disk)["description"] == "the edited one"

    def test_an_untouched_file_still_reads_from_disk(self, on_disk):
        resolution.use_overlay(_Overlay({"something/else.md": EDITED}))
        assert parse_frontmatter(on_disk)["body"] == "The shipped body."


def test_the_reader_is_the_shared_one():
    """Named, so the next markdown reader does not repeat this."""
    source = Path(parse_frontmatter.__code__.co_filename).read_text()
    assert "content = effective_text(path)" in source
    assert "content = path.read_text()" not in source
