"""E34-T3. Changing the configuration from the diagram."""

from __future__ import annotations

import pytest

from agent.src.config_surface.graph_edit import GraphEditRefused, propose

SUBAGENT = """---
name: curator
# Why this model: it is the cheap one and this subagent reads a lot.
model: old-model
skills:
  - data-discovery   # the only one that matters
---

You are a curator.
"""

MCP = """{
  // Three tools, about 540 tokens — cheaper to keep than to delegate.
  "mcpServers": {
    "keep": {"command": "x"},
    "off": {"command": "y", "disabled": true}
  }
}
"""


@pytest.fixture
def root(tmp_path):
    (tmp_path / "subagents").mkdir()
    (tmp_path / "subagents" / "curator.md").write_text(SUBAGENT)
    (tmp_path / "integrations").mkdir()
    (tmp_path / "integrations" / "mcp.json").write_text(MCP)
    return tmp_path


class TestChangingAModel:
    def test_it_rewrites_the_one_line(self, root):
        path, text = propose(
            node_id="subagent:curator", field="model", value="new-model", root=root
        )
        assert path == "config/agent/subagents/curator.md"
        assert "model: new-model" in text
        assert "model: old-model" not in text

    def test_everything_else_survives(self, root):
        """The comments are most of what the last author left behind."""
        _, text = propose(
            node_id="subagent:curator", field="model", value="new-model", root=root
        )
        assert "# Why this model: it is the cheap one" in text
        assert "# the only one that matters" in text
        assert "You are a curator." in text

    def test_a_subagent_with_no_model_gains_one(self, root):
        (root / "subagents" / "bare.md").write_text("---\nname: bare\n---\nbody\n")
        _, text = propose(node_id="subagent:bare", field="model", value="m", root=root)
        assert "model: m" in text
        assert text.endswith("body\n")

    def test_an_empty_model_is_not_a_change(self, root):
        with pytest.raises(GraphEditRefused, match="empty one is not a change"):
            propose(node_id="subagent:curator", field="model", value="  ", root=root)


class TestTurningAServerOff:
    def test_it_adds_disabled(self, root):
        path, text = propose(
            node_id="mcp:keep", field="enabled", value=False, root=root
        )
        assert path == "config/agent/integrations/mcp.json"
        assert '"disabled": true' in text.split('"off"')[0]

    def test_it_clears_disabled(self, root):
        _, text = propose(node_id="mcp:off", field="enabled", value=True, root=root)
        assert '"disabled": false' in text

    def test_the_comments_in_a_jsonc_file_survive(self, root):
        _, text = propose(node_id="mcp:keep", field="enabled", value=False, root=root)
        assert "// Three tools, about 540 tokens" in text

    def test_an_unknown_server_is_named(self, root):
        with pytest.raises(GraphEditRefused, match="no server named 'ghost'"):
            propose(node_id="mcp:ghost", field="enabled", value=False, root=root)


class TestWhatItRefuses:
    def test_a_list_is_refused_with_the_reason(self, root):
        """Rewriting a block would decide where its comments go."""
        with pytest.raises(GraphEditRefused, match="lose the comments"):
            propose(node_id="subagent:curator", field="skills", value=["x"], root=root)

    def test_a_kind_with_nothing_editable_says_so(self, root):
        with pytest.raises(GraphEditRefused, match="open its file"):
            propose(node_id="skill:data-discovery", field="model", value="m", root=root)

    def test_a_missing_subagent_is_named(self, root):
        with pytest.raises(GraphEditRefused, match="no subagent file for 'ghost'"):
            propose(node_id="subagent:ghost", field="model", value="m", root=root)

    def test_a_malformed_node_id_is_refused(self, root):
        with pytest.raises(GraphEditRefused, match="does not name a node"):
            propose(node_id="subagent", field="model", value="m", root=root)

    def test_enabled_must_be_a_boolean(self, root):
        with pytest.raises(GraphEditRefused, match="true or false"):
            propose(node_id="mcp:keep", field="enabled", value="no", root=root)


class TestItDoesNotWrite:
    def test_proposing_leaves_the_file_alone(self, root):
        before = (root / "subagents" / "curator.md").read_text()
        propose(node_id="subagent:curator", field="model", value="new", root=root)
        assert (root / "subagents" / "curator.md").read_text() == before


class TestRoundTrip:
    """E34-T5. Tree → diagram → tree is byte-identical when nothing"""

    def test_setting_a_model_to_what_it_already_is_changes_nothing(self, root):
        before = (root / "subagents" / "curator.md").read_text()
        _, text = propose(
            node_id="subagent:curator", field="model", value="old-model", root=root
        )
        assert text == before

    def test_enabling_an_already_enabled_server_changes_nothing(self, root):
        before = (root / "integrations" / "mcp.json").read_text()
        _, text = propose(node_id="mcp:keep", field="enabled", value=True, root=root)
        assert text == before

    def test_disabling_an_already_disabled_server_changes_nothing(self, root):
        before = (root / "integrations" / "mcp.json").read_text()
        _, text = propose(node_id="mcp:off", field="enabled", value=False, root=root)
        assert text == before

    def test_a_change_and_its_reverse_return_the_original(self, root):
        """Two edits through the diagram, back to the bytes it"""
        before = (root / "subagents" / "curator.md").read_text()
        _, changed = propose(
            node_id="subagent:curator", field="model", value="new-model", root=root
        )
        (root / "subagents" / "curator.md").write_text(changed)
        _, back = propose(
            node_id="subagent:curator", field="model", value="old-model", root=root
        )
        assert back == before
