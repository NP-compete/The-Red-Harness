"""`make validate-config` fails on the three things CFG-4 names."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agent.src.agent.config.paths import config_root
from agent.src.agent.config.validate import validate_config


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A copy of the shipped tree, to break one thing at a time."""
    made = tmp_path / "agent"
    shutil.copytree(config_root(), made)
    return made


def _agent_yaml(tree: Path) -> Path:
    return tree / "runtime" / "agent.yaml"


def _messages(tree: Path) -> list[str]:
    return [one.message for one in validate_config(tree).errors]


class TestItRefusesWhatCfg4Names:
    def test_the_shipped_tree_passes(self):
        assert not validate_config(config_root()).errors

    def test_an_unknown_top_level_key(self, tree):
        path = _agent_yaml(tree)
        path.write_text("whatever_this_is: 1\n" + path.read_text())

        found = _messages(tree)
        assert any("whatever_this_is" in one for one in found), found

    def test_a_mistyped_switch(self, tree):
        path = _agent_yaml(tree)
        # Written against `enabled: false`; the shipped tree now says
        # true, so the replace matched nothing and the file went to the
        # validator unmodified — the test failed having mistyped nothing.
        # Rewrite whichever boolean is there.
        source = path.read_text()
        for literal in ("knowledge:\n  enabled: false", "knowledge:\n  enabled: true"):
            if literal in source:
                quoted = (
                    literal.rsplit(" ", 1)[0] + ' "' + literal.rsplit(" ", 1)[1] + '"'
                )
                path.write_text(source.replace(literal, quoted, 1))
                break
        else:
            pytest.fail(f"no knowledge.enabled switch to mistype in {path}")

        found = _messages(tree)
        assert any("knowledge.enabled" in one for one in found), found

    def test_a_missing_required_file(self, tree):
        (tree / "PROMPT.md").unlink()

        found = _messages(tree)
        assert any("prompt" in one for one in found), found


class TestSectionsTheFileDrivesFromTheEnvironment:
    """Known, environment-driven, and deliberately not warned about."""

    ENV_DRIVEN = {"logging", "memory", "platform", "server"}

    def test_they_are_known_and_annotated(self):
        from agent.src.agent.config.validate import AGENT_SECTIONS

        for key in self.ENV_DRIVEN:
            assert AGENT_SECTIONS.get(key), f"{key} should be known and annotated"

    def test_the_note_names_what_decides_instead(self):
        from agent.src.agent.config.validate import AGENT_SECTIONS

        assert "PLATFORM_AUDIT_ENABLED" in AGENT_SECTIONS["platform"]
        assert "AGENT_PORT" in AGENT_SECTIONS["server"]

    def test_they_produce_no_findings(self):
        report = validate_config(config_root())
        assert not [one for one in report.errors if one.location in self.ENV_DRIVEN]
        assert not [one for one in report.warnings if one.location in self.ENV_DRIVEN]
