"""Telling somebody a setting is going away, while it still works."""

from __future__ import annotations

import pytest

from agent.src.agent.config.deprecations import (
    Deprecation,
    deprecations_in,
    reset_warnings,
    warn_once,
)
from agent.src.agent.config.problems import found_problems, reset_problems
from agent.src.agent.config.schema_version import CURRENT


@pytest.fixture(autouse=True)
def _clean():
    reset_problems()
    reset_warnings()
    yield
    reset_problems()
    reset_warnings()


def _flat(tmp_path):
    (tmp_path / "agent.yaml").write_text("name: a\n")
    return tmp_path


def _nested(tmp_path):
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "agent.yaml").write_text("name: a\n")
    return tmp_path


class TestTheOldFileLayout:
    def test_a_tree_on_it_is_told(self, tmp_path):
        found = deprecations_in({}, _flat(tmp_path))
        assert any("agent.yaml" in d.what for d in found)

    def test_it_names_what_to_use_instead(self, tmp_path):
        found = deprecations_in({}, _flat(tmp_path))
        assert any("runtime/agent.yaml" in (d.instead or "") for d in found)

    def test_it_names_the_version_it_goes_in(self, tmp_path):
        found = deprecations_in({}, _flat(tmp_path))
        assert all(d.removed_in > CURRENT for d in found)

    def test_a_tree_on_the_current_layout_is_left_alone(self, tmp_path):
        assert deprecations_in({}, _nested(tmp_path)) == []


class TestADeprecatedField:
    REGISTERED = Deprecation(
        what="guardrail.model",
        instead="guardrail.judge_model",
        removed_in=CURRENT + 1,
    )

    def test_a_tree_using_it_is_told(self, tmp_path):
        raw = {"guardrail": {"model": "x"}}
        found = deprecations_in(raw, _nested(tmp_path), fields=(self.REGISTERED,))
        assert found == [self.REGISTERED]

    def test_a_tree_not_using_it_is_left_alone(self, tmp_path):
        raw = {"guardrail": {"judge_model": "x"}}
        assert deprecations_in(raw, _nested(tmp_path), fields=(self.REGISTERED,)) == []

    def test_a_missing_section_is_not_a_use_of_the_field(self, tmp_path):
        assert deprecations_in({}, _nested(tmp_path), fields=(self.REGISTERED,)) == []

    def test_a_section_that_is_not_a_mapping_does_not_crash(self, tmp_path):
        raw = {"guardrail": "enabled"}
        assert deprecations_in(raw, _nested(tmp_path), fields=(self.REGISTERED,)) == []


class TestSayingItOnce:
    ONE = Deprecation(what="a.b", instead="a.c", removed_in=CURRENT + 1)

    def test_it_is_recorded_where_somebody_will_see_it(self):
        warn_once([self.ONE])
        assert any("a.b" in p.detail for p in found_problems())

    def test_the_record_says_what_to_use_instead(self):
        warn_once([self.ONE])
        assert any("a.c" in p.detail for p in found_problems())

    def test_the_record_names_the_version_it_goes_in(self):
        warn_once([self.ONE])
        assert any(str(CURRENT + 1) in p.detail for p in found_problems())

    def test_a_reload_does_not_say_it_again(self):
        for _ in range(5):
            warn_once([self.ONE])
        assert len([p for p in found_problems() if "a.b" in p.detail]) == 1

    def test_a_different_one_is_still_said(self):
        other = Deprecation(what="x.y", instead="x.z", removed_in=CURRENT + 1)
        warn_once([self.ONE])
        warn_once([other])
        assert len(found_problems()) == 2


class TestTheLoaderDoesIt:
    """The gap this exists to close: the validator warned and the"""

    def test_a_pod_on_the_old_layout_says_so(self, tmp_path, monkeypatch):
        from agent.src.agent.config.loader import agent_config

        (tmp_path / "agent.yaml").write_text(f"schema_version: {CURRENT}\nname: a\n")
        monkeypatch.setattr(agent_config, "_base_dir", tmp_path)
        agent_config._load_agent_yaml()
        assert any("agent.yaml" in p.detail for p in found_problems())
