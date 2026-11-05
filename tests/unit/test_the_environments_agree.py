"""What each environment builds and runs, pinned (CI-9)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI_DOC = ROOT / "docs" / "development" / "ci.md"
MAKEFILE = ROOT / "Makefile"
COMPOSE = ROOT / "compose.yaml"
BUILDCONFIG = ROOT / "deployment" / "overlays" / "openshift" / "buildconfig.yaml"


def _jobs(env: str) -> list[str]:
    out = subprocess.run(
        ["make", "--no-print-directory", "ci-jobs", f"ENV={env}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


class TestOneCommandPerEnvironment:
    def test_each_environment_adds_its_own_tier(self):
        assert "ci-compose" in _jobs("compose")
        assert "ci-kind" in _jobs("kind")

    def test_and_neither_tier_leaks_into_the_other(self):
        assert "ci-kind" not in _jobs("compose")
        assert "ci-compose" not in _jobs("kind")

    def test_the_rest_of_the_list_is_the_same_sentence(self):
        shared = set(_jobs("")) - {"ci-compose", "ci-kind"}
        for env in ("compose", "kind"):
            missing = shared - set(_jobs(env))
            assert not missing, (
                f"ENV={env} runs fewer checks than ENV= does: {sorted(missing)}. "
                "A green that means two different things is worse than a red."
            )

    def test_what_was_skipped_is_named(self):
        for env, expected in (("compose", "ci-kind"), ("kind", "ci-compose")):
            out = subprocess.run(
                ["make", "--no-print-directory", "ci-skipped", f"ENV={env}"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert expected in out.stdout, out.stdout


class TestTheOneEnvironmentTiersAreNamed:
    """CI-9's own escape clause, held to its wording."""

    def test_the_doc_names_both_with_a_reason(self):
        text = CI_DOC.read_text()
        for tier in ("ci-compose", "ci-kind"):
            assert tier in text, (
                f"{tier} runs in one environment and docs/development/ci.md is silent"
            )
        assert "Needs Postgres, Redis and OPA" in text
        assert "no kubelet to be wrong about" in text

    def test_it_names_the_tiers_in_neither_list(self):
        text = CI_DOC.read_text()
        assert "test-nightly" in text
        assert "make timings" in text
        refusal = "no measurement — is the loop running?"
        assert refusal in text
        assert refusal in (ROOT / "scripts" / "dev" / "timings.sh").read_text()


class TestTheImagesEachEnvironmentBuilds:
    """The clause CI-9 gives no escape for, measured."""

    def test_kind_builds_the_harness_runtime_stage(self):
        assert "-f Containerfile --target runtime" in MAKEFILE.read_text()

    def test_the_ci_image_is_the_harness_ci_stage(self):
        assert "-f Containerfile --target ci" in MAKEFILE.read_text()

    def test_compose_still_builds_the_other_containerfile(self):
        agent = re.search(
            r"^  template-agent:\n(?:.*\n)*?^  \S",
            COMPOSE.read_text(),
            re.MULTILINE,
        )
        assert agent, "no template-agent service in compose.yaml"
        block = agent.group(0)
        assert "dockerfile: Containerfile\n" in block, (
            "compose no longer builds `Containerfile`. If it moved to "
            "Containerfile --target runtime that is the CI-9 gap "
            "closing — update the table in docs/development/ci.md and this test."
        )

    def test_openshift_builds_the_same_one_compose_does(self):
        assert "dockerfilePath: Containerfile\n" in BUILDCONFIG.read_text()

    def test_the_divergence_is_written_down_not_implied(self):
        text = CI_DOC.read_text()
        assert "compose agrees with production and disagrees with kind" in text.lower()
        assert "Containerfile" in text
