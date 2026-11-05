"""CFG-7's two halves, as something that can fail."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ci"))

import feature_registry  # noqa: E402

REGISTRY = ROOT / "config/agent/runtime/features.yaml"


@pytest.fixture
def elsewhere(tmp_path, monkeypatch):
    """Point the check at a tree we can break."""
    config = tmp_path / "config"
    (config / "agent/runtime").mkdir(parents=True)
    monkeypatch.setattr(feature_registry, "CONFIG", config)
    monkeypatch.setattr(
        feature_registry, "REGISTRY", config / "agent/runtime/features.yaml"
    )
    return config


def _write(config: Path, registry: dict, extra: dict | None = None) -> None:
    (config / "agent/runtime/features.yaml").write_text(
        yaml.safe_dump({"features": registry})
    )
    if extra is not None:
        (config / "agent/runtime/agent.yaml").write_text(yaml.safe_dump(extra))


SOUND = {"planner_enabled": {"epic": "E14", "default": False, "scope": "agent"}}


class TestTheShippedTree:
    def test_it_passes(self):
        assert feature_registry.problems() == []

    def test_every_entry_names_an_epic(self):
        declared = yaml.safe_load(REGISTRY.read_text())["features"]
        missing = [k for k, v in declared.items() if not v.get("epic")]
        assert missing == [], missing


class TestItRefusesWhatCfg7Names:
    def test_a_flag_with_no_registry_entry(self, elsewhere):
        _write(elsewhere, SOUND, {"features": {"invented_enabled": True}})

        found = feature_registry.problems()
        assert any("invented_enabled" in one for one in found), found

    def test_a_registry_entry_with_no_epic(self, elsewhere):
        _write(elsewhere, {"planner_enabled": {"default": False, "scope": "agent"}})

        found = feature_registry.problems()
        assert any("owning epic" in one for one in found), found

    def test_a_flag_that_ships_on(self, elsewhere):
        _write(elsewhere, {"planner_enabled": {"epic": "E14", "default": True}})

        found = feature_registry.problems()
        assert any("default to false" in one for one in found), found

    def test_a_sound_registry_is_quiet(self, elsewhere):
        _write(elsewhere, SOUND, {"features": {"planner_enabled": True}})

        assert feature_registry.problems() == []


class TestTheInterfaceHasItsOwn:
    """`ui.yaml` carries a `features:` block that is not this one."""

    def test_ui_yaml_is_excluded(self):
        assert "runtime/ui.yaml" in feature_registry.NOT_THE_REGISTRY

    def test_and_its_flag_is_not_demanded_of_the_registry(self):
        assert "mcp_apps_enabled" not in feature_registry.used()
