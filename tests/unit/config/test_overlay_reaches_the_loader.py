"""An edit changes what the agent reads, not just what the store holds."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agent.src.agent.config import loader
from agent.src.agent.config.overlay import InMemoryOverlay
from agent.src.agent.config.resolution import overlay_key, use_overlay


@pytest.fixture(autouse=True)
def _no_overlay():
    use_overlay(None)
    yield
    use_overlay(None)


class TestEveryConfigReadGoesThroughOneDoor:
    def test_the_loader_does_not_read_a_config_file_directly(self):
        import inspect

        source = inspect.getsource(loader)
        offending = [
            line.strip()
            for line in source.splitlines()
            if ".read_text()" in line
            and "_config_text" not in line
            and not line.strip().startswith(("#", "*", '"', "'"))
            and "`path.read_text()`" not in line
        ]
        assert offending == [], (
            "these read a config file without going through the resolver, so "
            f"an edit to them would be ignored: {offending}"
        )

    def test_the_resolver_is_what_it_goes_through(self):
        import inspect

        assert "effective_text" in inspect.getsource(loader._config_text)


class TestAnEditReachesTheLoader:
    def test_the_loader_sees_the_overlaid_text(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
        path = tmp_path / "runtime" / "pii.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(yaml.safe_dump({"pii": {"enabled": False}}))

        assert yaml.safe_load(loader._config_text(path))["pii"]["enabled"] is False

        overlay = InMemoryOverlay()
        overlay.apply(
            overlay_key(path),
            yaml.safe_dump({"pii": {"enabled": True}}),
            author="ada",
        )
        use_overlay(overlay)

        assert yaml.safe_load(loader._config_text(path))["pii"]["enabled"] is True


class TestWithNothingEditedItIsInvisible:
    def test_the_text_is_what_the_file_says(self, tmp_path):
        path: Path = tmp_path / "anything.yaml"
        path.write_text("a:   1   \n\n# trailing comment\n")
        assert loader._config_text(path) == path.read_text()

    def test_even_with_an_overlay_holding_other_paths(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CONFIG_PATH", str(tmp_path))
        path = tmp_path / "runtime" / "agent.yaml"
        path.parent.mkdir(parents=True)
        path.write_text("name: tracker\n")

        overlay = InMemoryOverlay()
        overlay.apply("config/agent/runtime/router.yaml", "something", author="ada")
        use_overlay(overlay)

        assert loader._config_text(path) == "name: tracker\n"
