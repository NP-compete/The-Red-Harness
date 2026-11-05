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
    """One gated tier now, not two.

    `ci-compose` used to be the other: it needed Postgres, Redis and
    OPA reachable on the host, so it only ran where somebody had
    brought them up. It is `compose_tier` in the Dagger module now
    and binds its own, so it runs everywhere and is gated by
    nothing. A cluster is still a cluster.
    """

    def test_the_cluster_tier_is_the_gated_one(self):
        assert "ci-kind" in _jobs("kind")

    def test_the_integration_tier_is_not_gated_by_an_environment(self):
        """`ci-compose` runs anywhere now; it is only gated by time.

        It used to need a compose network somebody had brought up by
        hand, so it sat behind `ENV=compose` and on most laptops ran
        never. `compose_tier` binds its own Postgres, Redis and
        agent. It is still a job of its own rather than part of
        `make ci`, because three services is minutes and `ci` should
        answer fast — not because any environment is missing.
        """
        for env in ("", "compose", "kind"):
            assert "ci-compose" not in _jobs(env), (
                "ci-compose is environment-gated again; it no longer "
                "needs an environment, only its own timeout"
            )

    def test_the_cluster_tier_does_not_leak_into_the_default_list(self):
        assert "ci-kind" not in _jobs("")

    def test_the_rest_of_the_list_is_the_same_sentence(self):
        shared = set(_jobs("")) - {"ci-kind"}
        for env in ("compose", "kind"):
            missing = shared - set(_jobs(env))
            assert not missing, (
                f"ENV={env} runs fewer checks than ENV= does: {sorted(missing)}. "
                "A green that means two different things is worse than a red."
            )

    def test_what_was_skipped_is_named(self):
        out = subprocess.run(
            ["make", "--no-print-directory", "ci-skipped"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert "ci-kind" in out.stdout, out.stdout


class TestTheOneEnvironmentTiersAreNamed:
    """CI-9's own escape clause, held to its wording."""

    def test_the_doc_names_both_with_a_reason(self):
        text = CI_DOC.read_text()
        for tier in ("ci-compose", "ci-kind"):
            assert tier in text, (
                f"{tier} runs in one environment and docs/development/ci.md is silent"
            )
        assert "Needs Postgres, Redis and a running agent" in text
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
