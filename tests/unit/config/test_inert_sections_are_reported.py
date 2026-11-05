"""`/config/file` names the sections the file does not decide."""

from __future__ import annotations

from agent.aegra.config_editing_routes import _inert_in
from agent.src.agent.config.validate import AGENT_SECTIONS

AGENT_YAML = "config/agent/runtime/agent.yaml"


class TestWhatItReports:
    def test_a_section_the_file_does_not_decide(self):
        found = _inert_in(AGENT_YAML, "platform:\n  audit:\n    enabled: false\n")

        assert [one["section"] for one in found] == ["platform"]
        assert "PLATFORM_AUDIT_ENABLED" in found[0]["decided_by"]

    def test_a_section_the_file_does_decide(self):
        assert _inert_in(AGENT_YAML, "knowledge:\n  enabled: false\n") == []

    def test_the_shipped_tree_reports_exactly_four(self):
        from agent.src.agent.config.paths import config_root

        text = (config_root() / "runtime" / "agent.yaml").read_text()
        found = {one["section"] for one in _inert_in(AGENT_YAML, text)}
        assert found == {"logging", "memory", "platform", "server"}, found


class TestWhatItDoesNotDo:
    def test_another_file_is_left_alone(self):
        assert _inert_in("config/agent/runtime/router.yaml", "memory:\n  a: 1\n") == []

    def test_text_that_is_not_yaml_yet(self):
        assert _inert_in(AGENT_YAML, "platform:\n  audit: [\n") == []

    def test_an_empty_file(self):
        assert _inert_in(AGENT_YAML, "") == []


class TestItAgreesWithTheValidator:
    def test_every_section_it_names_is_annotated_there(self):
        from agent.src.agent.config.paths import config_root

        text = (config_root() / "runtime" / "agent.yaml").read_text()
        for one in _inert_in(AGENT_YAML, text):
            assert AGENT_SECTIONS[one["section"]] == one["decided_by"]
