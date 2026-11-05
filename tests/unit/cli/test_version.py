"""One version, reported by both ends (E28-T11, E10 strand D)."""

from __future__ import annotations

from agent.cli.doctor import Severity, diagnose
from agent.version import UNKNOWN, same_as, version


class TestTheNumber:
    def test_there_is_one(self):
        assert version() and version() != UNKNOWN

    def test_it_is_the_package_version_not_a_copy_of_it(self):
        import tomllib
        from pathlib import Path

        here = Path(__file__).resolve().parents[3] / "pyproject.toml"
        declared = tomllib.loads(here.read_text())["project"]["version"]
        assert version() == declared


class TestWhatADeploymentSets:
    def test_application_version_wins(self, monkeypatch):
        monkeypatch.setenv("APPLICATION_VERSION", "9.9.9-rc1")
        assert version() == "9.9.9-rc1"

    def test_aegra_reads_the_same_function(self, monkeypatch):
        import agent.aegra as aegra

        assert aegra.__version__ == version()


class TestComparing:
    def test_the_same_version_agrees(self):
        assert same_as(version())

    def test_a_different_one_does_not(self):
        assert not same_as("0.0.1-nope")

    def test_an_agent_that_does_not_say_is_not_a_mismatch(self):
        assert same_as("")
        assert same_as(UNKNOWN)


class TestWhatDoctorSays:
    def test_a_mismatch_is_reported_and_names_the_fix(self):
        found = diagnose({"agent_reachable": True, "versions_agree": False})
        assert [one.name for one in found] == ["versions_agree"]
        assert "Reinstall" in found[0].remedy
        assert found[0].severity is Severity.DEGRADED

    def test_agreement_is_silent(self):
        assert diagnose({"agent_reachable": True, "versions_agree": True}) == []

    def test_an_agent_that_cannot_say_is_left_out_entirely(self):
        assert diagnose({"agent_reachable": True}) == []
