"""A tree in the pre-rename layout still loads (CFG-2)."""

from __future__ import annotations

import shutil

import pytest

from agent.src.agent.config.paths import _CANDIDATES

RENAMED = [
    "agent",
    "filesystem",
    "guardrails",
    "mcp",
    "memory_instructions",
    "observability",
    "pii",
    "router",
    "ui",
]


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    """The shipped tree, with every renamed file put back."""
    from agent.src.agent.config.paths import config_root

    tree = tmp_path / "agent"
    shutil.copytree(config_root(), tree)
    for name in RENAMED:
        preferred, older = _CANDIDATES[name][0], _CANDIDATES[name][1]
        if (tree / preferred).is_file():
            (tree / older).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tree / preferred), str(tree / older))

    monkeypatch.setenv("CONFIG_PATH", str(tree))
    from agent.src.agent.config.loader import AgentConfig

    return AgentConfig(tree)


class TestTheTableItself:
    def test_every_name_here_still_has_a_legacy_candidate(self):
        for name in RENAMED:
            where = _CANDIDATES.get(name)
            assert where and len(where) > 1, (
                f"{name} no longer offers a legacy path. Either the rename "
                "is complete and this list should lose it deliberately, or "
                "a tree that has not been renamed has just stopped loading."
            )

    def test_and_no_other_name_has_one(self):
        offering = sorted(n for n, w in _CANDIDATES.items() if len(w) > 1)
        assert offering == RENAMED, offering


class TestItLoads:
    def test_the_agent_has_its_name(self, legacy):
        assert legacy.get_name()

    def test_the_subagents_are_there(self, legacy):
        assert legacy.get_all_subagent_configs()

    def test_the_mcp_servers_are_there(self, legacy):
        assert legacy.get_mcp_servers()

    def test_a_section_of_the_agent_file_is_read(self, legacy):
        assert legacy.get_knowledge_config() is not None


class TestItIsStillReportedAsOld:
    def test_every_renamed_file_is_named(self, tmp_path, monkeypatch):
        from agent.src.agent.config.paths import config_root, describe_layout

        tree = tmp_path / "agent"
        shutil.copytree(config_root(), tree)
        for name in RENAMED:
            preferred, older = _CANDIDATES[name][0], _CANDIDATES[name][1]
            if (tree / preferred).is_file():
                (tree / older).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(tree / preferred), str(tree / older))
        monkeypatch.setenv("CONFIG_PATH", str(tree))

        said = {name for name, about in describe_layout().items() if about["legacy"]}
        expected = {name for name in RENAMED if (tree / _CANDIDATES[name][1]).is_file()}
        assert said == expected, (said, expected)

    def test_the_shipped_tree_reports_none(self):
        from agent.src.agent.config.paths import describe_layout

        assert not [n for n, about in describe_layout().items() if about["legacy"]]
