"""The version a tree declares, checked when the tree is read."""

from __future__ import annotations

import pytest

from agent.src.agent.config.problems import found_problems, reset_problems
from agent.src.agent.config.schema_version import CURRENT, OLDEST_SUPPORTED


@pytest.fixture(autouse=True)
def _clean():
    reset_problems()
    yield
    reset_problems()


def _load(tmp_path, text, monkeypatch):
    """Point the loader at a whole tree, not only one file."""
    from agent.src.agent.config.loader import agent_config

    tree = tmp_path / "runtime"
    tree.mkdir()
    (tree / "agent.yaml").write_text(text)
    (tmp_path / "PROMPT.md").write_text("You are an agent.\n")
    (tmp_path / "integrations").mkdir()
    (tmp_path / "integrations" / "mcp.json").write_text("{}")
    monkeypatch.setattr(agent_config, "_base_dir", tmp_path)
    monkeypatch.setattr(agent_config, "_configs_loaded", False)
    return agent_config._load_agent_yaml()


class TestATreeInsideTheWindow:
    def test_the_current_version_loads(self, tmp_path, monkeypatch):
        raw = _load(tmp_path, f"schema_version: {CURRENT}\nname: a\n", monkeypatch)
        assert raw["name"] == "a"

    def test_the_previous_version_still_loads(self, tmp_path, monkeypatch):
        raw = _load(
            tmp_path, f"schema_version: {OLDEST_SUPPORTED}\nname: a\n", monkeypatch
        )
        assert raw["name"] == "a"

    def test_the_previous_version_says_so(self, tmp_path, monkeypatch):
        _load(tmp_path, f"schema_version: {OLDEST_SUPPORTED}\nname: a\n", monkeypatch)
        assert any("schema" in p.detail.lower() for p in found_problems())

    def test_the_current_version_is_not_a_problem(self, tmp_path, monkeypatch):
        _load(tmp_path, f"schema_version: {CURRENT}\nname: a\n", monkeypatch)
        assert found_problems() == []


class TestATreeWithNoVersion:
    """No tree carries the field yet, and the first rollout must not"""

    def test_it_loads(self, tmp_path, monkeypatch):
        raw = _load(tmp_path, "name: a\n", monkeypatch)
        assert raw["name"] == "a"

    def test_it_is_read_as_the_oldest_shape_and_said_so(self, tmp_path, monkeypatch):
        _load(tmp_path, "name: a\n", monkeypatch)
        assert any("schema" in p.detail.lower() for p in found_problems())


class TestATreeOutsideTheWindow:
    def test_a_newer_tree_stops_the_agent(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import ConfigVersionUnsupported

        with pytest.raises(ConfigVersionUnsupported):
            _load(tmp_path, f"schema_version: {CURRENT + 1}\n", monkeypatch)

    def test_a_newer_tree_says_to_upgrade_the_deployment(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import ConfigVersionUnsupported

        with pytest.raises(ConfigVersionUnsupported, match="[Uu]pgrade"):
            _load(tmp_path, f"schema_version: {CURRENT + 1}\n", monkeypatch)

    def test_an_older_tree_stops_the_agent(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import ConfigVersionUnsupported

        with pytest.raises(ConfigVersionUnsupported):
            _load(tmp_path, f"schema_version: {OLDEST_SUPPORTED - 1}\n", monkeypatch)

    def test_an_older_tree_says_to_migrate_it(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import ConfigVersionUnsupported

        with pytest.raises(ConfigVersionUnsupported, match="[Mm]igrate"):
            _load(tmp_path, f"schema_version: {OLDEST_SUPPORTED - 1}\n", monkeypatch)

    def test_it_is_a_reason_the_agent_will_not_start(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import AgentConfigUnreadable

        with pytest.raises(AgentConfigUnreadable):
            _load(tmp_path, f"schema_version: {CURRENT + 1}\n", monkeypatch)


class TestAVersionThatIsNotANumber:
    def test_it_is_refused_rather_than_guessed_at(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import ConfigVersionUnsupported

        with pytest.raises(ConfigVersionUnsupported):
            _load(tmp_path, "schema_version: three\n", monkeypatch)

    def test_the_message_names_the_field(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import ConfigVersionUnsupported

        with pytest.raises(ConfigVersionUnsupported, match="schema_version"):
            _load(tmp_path, "schema_version: three\n", monkeypatch)


class TestWhatTheTreeDeclared:
    """An operator comparing a pod against its configuration."""

    def test_the_declared_version_is_readable(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import agent_config

        _load(tmp_path, f"schema_version: {CURRENT}\nname: a\n", monkeypatch)
        assert agent_config.declared_schema_version() == CURRENT

    def test_a_tree_with_no_field_declares_nothing(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import agent_config

        _load(tmp_path, "name: a\n", monkeypatch)
        assert agent_config.declared_schema_version() is None


class TestTheShippedTree:
    def test_it_declares_a_version(self):
        import yaml

        from agent.src.agent.config.loader import agent_config

        raw = yaml.safe_load(
            (agent_config.base_dir / "runtime" / "agent.yaml").read_text()
        )
        assert raw.get("schema_version") == CURRENT
