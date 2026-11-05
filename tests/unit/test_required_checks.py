"""The required checks name jobs that exist (E26-T10)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2] / ".github"
DECLARATION = ROOT / "required-checks.yml"
WORKFLOWS = ROOT / "workflows"


def _declared() -> dict:
    return yaml.safe_load(DECLARATION.read_text())


def _names_in(workflow: str) -> set[str]:
    """Every check name one workflow can report."""
    body = yaml.safe_load((WORKFLOWS / workflow).read_text()) or {}
    return {job.get("name", key) for key, job in (body.get("jobs") or {}).items()}


class TestTheDeclaration:
    def test_it_exists_and_parses(self):
        assert _declared()["required"]

    def test_every_required_check_is_a_job_that_exists(self):
        missing = []
        for entry in _declared()["required"]:
            names = _names_in(entry["workflow"])
            missing += [
                f"{entry['workflow']}: {one}"
                for one in entry["checks"]
                if one not in names
            ]
        assert missing == [], f"required checks that no job reports: {missing}"

    def test_so_is_the_conditional_one(self):
        for entry in _declared().get("conditional") or []:
            assert entry["check"] in _names_in(entry["workflow"]), entry

    def test_the_conditional_tier_says_when_it_runs(self):
        for entry in _declared().get("conditional") or []:
            assert entry.get("when", "").strip()

    def test_every_advisory_check_says_why_it_is_not_required(self):
        for entry in _declared().get("advisory") or []:
            assert entry.get("why", "").strip(), entry


class TestWhatItCovers:
    # "Test Suite" and "Config, contract and deployment" were two
    # jobs; they are one Dagger call reported as "Checks" now.
    @pytest.mark.parametrize("check", ["Checks", "Integration (compose)"])
    def test_the_tiers_that_run_on_every_pull_request_are_required(self, check):
        required = {one for entry in _declared()["required"] for one in entry["checks"]}
        assert check in required

    def test_the_cluster_tier_is_required_rather_than_advisory(self):
        conditional = {one["check"] for one in _declared().get("conditional") or []}
        advisory = {one["check"] for one in _declared().get("advisory") or []}
        assert "Cluster (kind)" in conditional
        assert "Cluster (kind)" not in advisory
