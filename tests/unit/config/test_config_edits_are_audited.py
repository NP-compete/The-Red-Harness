"""Every configuration change leaves a trail, and the trail is safe."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from agent.src.agent.config import editing
from agent.src.agent.config.editing import EditRefused, apply_all
from agent.src.agent.config.overlay import InMemoryOverlay
from agent.src.agent.config.resolution import use_overlay

AGENT = "config/agent/runtime/agent.yaml"
PII = "config/agent/runtime/pii.yaml"
PROMPT = "config/agent/PROMPT.md"


@pytest.fixture(autouse=True)
def _clean():
    use_overlay(None)
    yield
    use_overlay(None)


@pytest.fixture
def tree(tmp_path: Path, monkeypatch) -> Path:
    source = Path(__file__).resolve().parents[3] / "config" / "agent"
    destination = tmp_path / "agent"
    shutil.copytree(source, destination)
    monkeypatch.setenv("CONFIG_PATH", str(destination))
    return destination


@pytest.fixture
def recorded(monkeypatch) -> list[tuple[str, dict]]:
    """Every audit event raised while a test runs."""
    seen: list[tuple[str, dict]] = []

    def emit(event_type: str, **details) -> None:
        seen.append((event_type, details))

    monkeypatch.setattr(editing, "emit_audit_event", emit)
    return seen


def _sound() -> str:
    return yaml.safe_dump({"enabled": True})


class TestAnEditThatIsKept:
    def test_it_is_recorded(self, tree, recorded):
        apply_all(InMemoryOverlay(), {PII: _sound()}, author="ada")
        assert len(recorded) == 1

    def test_the_record_names_the_path(self, tree, recorded):
        apply_all(InMemoryOverlay(), {PII: _sound()}, author="ada")
        assert recorded[0][1]["path"] == PII

    def test_the_record_names_who(self, tree, recorded):
        apply_all(InMemoryOverlay(), {PII: _sound()}, author="ada")
        assert recorded[0][1]["author"] == "ada"

    def test_the_record_names_the_version(self, tree, recorded):
        overlay = InMemoryOverlay()
        apply_all(overlay, {PII: _sound()}, author="ada")
        apply_all(overlay, {PII: yaml.safe_dump({"enabled": False})}, author="bo")
        assert [one[1]["version"] for one in recorded] == [1, 2]

    def test_the_record_is_timed(self, tree, recorded):
        apply_all(InMemoryOverlay(), {PII: _sound()}, author="ada")
        assert recorded[0][1]["at"]

    def test_each_path_in_a_set_gets_its_own_record(self, tree, recorded):
        apply_all(
            InMemoryOverlay(),
            {PII: _sound(), AGENT: (tree / "runtime" / "agent.yaml").read_text()},
            author="ada",
        )
        assert sorted(one[1]["path"] for one in recorded) == sorted([AGENT, PII])


class TestTheContentStaysOutOfIt:
    def test_the_new_text_is_not_in_the_record(self, tree, recorded):
        apply_all(
            InMemoryOverlay(),
            {PROMPT: "You are helpful. Token: hunter2-not-a-real-secret\n"},
            author="ada",
        )
        assert "hunter2" not in str(recorded[0])

    def test_a_fingerprint_is_recorded_instead(self, tree, recorded):
        apply_all(InMemoryOverlay(), {PII: _sound()}, author="ada")
        assert recorded[0][1]["fingerprint"]

    def test_two_different_contents_fingerprint_differently(self, tree, recorded):
        overlay = InMemoryOverlay()
        apply_all(overlay, {PII: yaml.safe_dump({"enabled": True})}, author="ada")
        apply_all(overlay, {PII: yaml.safe_dump({"enabled": False})}, author="ada")
        assert recorded[0][1]["fingerprint"] != recorded[1][1]["fingerprint"]

    def test_the_same_content_fingerprints_the_same(self, tree, recorded):
        overlay = InMemoryOverlay()
        apply_all(overlay, {PII: _sound()}, author="ada")
        apply_all(overlay, {PII: _sound()}, author="bo")
        assert recorded[0][1]["fingerprint"] == recorded[1][1]["fingerprint"]

    def test_the_fingerprint_is_not_the_content_in_disguise(self, tree, recorded):
        apply_all(InMemoryOverlay(), {PII: _sound()}, author="ada")
        assert len(recorded[0][1]["fingerprint"]) <= 64


class TestAnEditThatIsRefused:
    def test_it_is_recorded_too(self, tree, recorded):
        with pytest.raises(EditRefused):
            apply_all(InMemoryOverlay(), {PII: "enabled: perhaps\n"}, author="ada")
        assert recorded

    def test_it_is_a_different_kind_of_record(self, tree, recorded):
        with pytest.raises(EditRefused):
            apply_all(InMemoryOverlay(), {PII: "enabled: perhaps\n"}, author="ada")
        assert recorded[0][0] != "config_edited"

    def test_it_names_who_tried_and_what(self, tree, recorded):
        with pytest.raises(EditRefused):
            apply_all(InMemoryOverlay(), {PII: "enabled: perhaps\n"}, author="ada")
        assert recorded[0][1]["author"] == "ada"
        assert PII in recorded[0][1]["paths"]

    def test_the_refused_content_is_not_in_it_either(self, tree, recorded):
        with pytest.raises(EditRefused):
            apply_all(
                InMemoryOverlay(),
                {PII: "enabled: hunter2-not-a-real-secret\n"},
                author="ada",
            )
        assert "hunter2" not in str(recorded)


class TestTheTrailNeverBreaksTheEdit:
    def test_an_edit_still_applies_when_the_trail_cannot_be_written(
        self, tree, monkeypatch
    ):
        def explode(*_args, **_kwargs):
            raise RuntimeError("the audit sink is unreachable")

        monkeypatch.setattr(editing, "emit_audit_event", explode)
        overlay = InMemoryOverlay()
        apply_all(overlay, {PII: _sound()}, author="ada")
        assert overlay.current(PII)


class TestNothingIsRecordedWhenNothingHappens:
    def test_an_empty_set_records_nothing(self, tree, recorded):
        apply_all(InMemoryOverlay(), {}, author="ada")
        assert recorded == []
