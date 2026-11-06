"""E34-T1/T2/T4. The configuration as a graph, read from this tree."""

from __future__ import annotations

import inspect

import pytest

from agent.src.config_surface import graph_model


def _write(root, path: str, text: str) -> None:
    f = root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)


@pytest.fixture
def tree(tmp_path, monkeypatch):
    _write(tmp_path, "runtime/agent.yaml", "name: test-agent\nmodel:\n  name: m1\n")
    _write(
        tmp_path,
        "subagents/curator.md",
        "---\nname: curator\nskills:\n  - real\n  - gone\nmcps:\n  - here\n---\nbody\n",
    )
    _write(tmp_path, "skills/real/SKILL.md", "---\nname: real\n---\n")
    _write(tmp_path, "integrations/mcp.json", '{"mcpServers": {"here": {}}}')
    monkeypatch.setattr(graph_model, "config_root", lambda: tmp_path)
    return tmp_path


class TestWhatItDraws:
    def test_the_tree_becomes_nodes(self, tree):
        found = graph_model.build_graph()
        labels = {n["label"] for n in found["nodes"]}
        assert {"test-agent", "curator", "real", "here", "m1"} <= labels

    def test_a_node_carries_the_file_it_came_from(self, tree):
        """Which is what lets clicking a box open that file."""
        found = graph_model.build_graph()
        curator = next(n for n in found["nodes"] if n["label"] == "curator")
        assert curator["path"] == "subagents/curator.md"

    def test_the_palette_is_what_the_tree_contains(self, tree):
        """E34-T2: a kind appears because the tree has one, not"""
        found = graph_model.build_graph()
        assert found["element_types"] == sorted(found["counts"])
        assert "subagent" in found["element_types"]


class TestWhatItDoesWithWhatIsWrong:
    def test_a_missing_skill_is_a_ghost_with_a_reason(self, tree):
        found = graph_model.build_graph()
        ghost = next(n for n in found["nodes"] if n["id"] == "skill:gone")
        assert ghost["missing"] is True
        assert any("gone" in p["what"] for p in found["problems"])

    def test_the_rest_of_the_graph_survives_one_bad_file(self, tree):
        """One unparseable file becomes one problem, not an empty"""
        (tree / "subagents" / "broken.md").write_text("---\nname: [unclosed\n---\n")
        found = graph_model.build_graph()
        assert any(n["label"] == "curator" for n in found["nodes"])
        assert found["problems"]

    def test_a_bare_model_string_does_not_crash_the_builder(self, tree):
        """The shipped tree uses the mapping form, so this shape is"""
        (tree / "runtime" / "agent.yaml").write_text("name: test-agent\nmodel: m2\n")
        found = graph_model.build_graph()
        assert any(n["label"] == "m2" for n in found["nodes"])


class TestItIsAViewNotASecondTruth:
    def test_it_reads_the_same_root_the_editor_writes(self):
        source = inspect.getsource(graph_model)
        assert "from agent.src.agent.config.paths import config_root" in source

    def test_nothing_is_cached_between_calls(self, tree):
        first = graph_model.build_graph()
        (tree / "skills" / "second").mkdir()
        (tree / "skills" / "second" / "SKILL.md").write_text("---\nname: second\n---\n")
        assert len(graph_model.build_graph()["nodes"]) == len(first["nodes"]) + 1
