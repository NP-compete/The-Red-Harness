"""An edit is checked before it is kept, and all of it or none."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agent.src.agent.config.editing import EditRefused, apply_all
from agent.src.agent.config.overlay import InMemoryOverlay
from agent.src.agent.config.resolution import use_overlay

AGENT = "config/agent/runtime/agent.yaml"
PII = "config/agent/runtime/pii.yaml"


@pytest.fixture(autouse=True)
def _clean():
    use_overlay(None)
    yield
    use_overlay(None)


@pytest.fixture
def tree(tmp_path: Path, monkeypatch) -> Path:
    """A copy of the shipped configuration tree."""
    import shutil

    source = Path(__file__).resolve().parents[3] / "config" / "agent"
    destination = tmp_path / "agent"
    shutil.copytree(source, destination)
    monkeypatch.setenv("CONFIG_PATH", str(destination))
    return destination


class TestAnEditThatIsSound:
    def test_it_is_kept(self, tree):
        overlay = InMemoryOverlay()
        apply_all(
            overlay,
            {PII: yaml.safe_dump({"enabled": True})},
            author="ada",
        )
        assert overlay.current(PII)

    def test_it_is_recorded_as_a_version(self, tree):
        overlay = InMemoryOverlay()
        apply_all(
            overlay,
            {PII: yaml.safe_dump({"enabled": True})},
            author="ada",
        )
        assert [one.version for one in overlay.history(PII)] == [1]


class TestAnEditThatIsNot:
    def _bad(self) -> str:
        return yaml.safe_dump({"enabled": "perhaps"})

    def test_it_is_refused(self, tree):
        with pytest.raises(EditRefused):
            apply_all(InMemoryOverlay(), {PII: self._bad()}, author="ada")

    def test_nothing_is_kept(self, tree):
        overlay = InMemoryOverlay()
        with pytest.raises(EditRefused):
            apply_all(overlay, {PII: self._bad()}, author="ada")
        assert overlay.history(PII) == []

    def test_the_refusal_names_the_file(self, tree):
        with pytest.raises(EditRefused) as raised:
            apply_all(InMemoryOverlay(), {PII: self._bad()}, author="ada")
        assert "pii" in str(raised.value).lower()

    def test_the_refusal_names_the_field(self, tree):
        with pytest.raises(EditRefused) as raised:
            apply_all(InMemoryOverlay(), {PII: self._bad()}, author="ada")
        assert "enabled" in str(raised.value)


class TestAllOfItOrNone:
    def test_one_bad_file_refuses_the_whole_set(self, tree):
        overlay = InMemoryOverlay()
        with pytest.raises(EditRefused):
            apply_all(
                overlay,
                {
                    PII: yaml.safe_dump({"enabled": True}),
                    AGENT: "not: [valid",
                },
                author="ada",
            )
        assert overlay.history(PII) == []
        assert overlay.history(AGENT) == []

    def test_the_sound_half_is_not_quietly_kept(self, tree):
        overlay = InMemoryOverlay()
        with pytest.raises(EditRefused):
            apply_all(
                overlay,
                {PII: yaml.safe_dump({"enabled": True}), AGENT: "not: ["},
                author="ada",
            )
        assert overlay.overridden() == []


class TestWhatWasAlreadyThereIsUnharmed:
    def test_an_earlier_edit_survives_a_later_refusal(self, tree):
        overlay = InMemoryOverlay()
        apply_all(overlay, {PII: yaml.safe_dump({"enabled": True})}, author="ada")
        with pytest.raises(EditRefused):
            apply_all(
                overlay,
                {PII: yaml.safe_dump({"enabled": "perhaps"})},
                author="bo",
            )
        assert yaml.safe_load(overlay.current(PII))["enabled"] is True
        assert [one.version for one in overlay.history(PII)] == [1]

    def test_the_overlay_in_use_is_put_back_after_a_refusal(self, tree):
        from agent.src.agent.config import resolution

        overlay = InMemoryOverlay()
        use_overlay(overlay)
        with pytest.raises(EditRefused):
            apply_all(overlay, {PII: "not: ["}, author="ada")
        assert resolution._overlay is overlay


class TestValidationSeesTheOverlay:
    def test_a_tree_made_valid_only_by_an_edit_is_accepted(self, tree):
        broken = tree / "runtime" / "pii.yaml"
        broken.write_text("enabled: perhaps\n")

        overlay = InMemoryOverlay()
        apply_all(overlay, {PII: yaml.safe_dump({"enabled": True})}, author="ada")
        assert overlay.current(PII)


class TestTheCheckCanFail:
    def test_a_sound_edit_really_does_get_through(self, tree):
        overlay = InMemoryOverlay()
        apply_all(overlay, {PII: yaml.safe_dump({"enabled": True})}, author="ada")
        assert overlay.overridden() == [PII]

    def test_an_empty_set_changes_nothing_and_does_not_raise(self, tree):
        overlay = InMemoryOverlay()
        apply_all(overlay, {}, author="ada")
        assert overlay.overridden() == []
