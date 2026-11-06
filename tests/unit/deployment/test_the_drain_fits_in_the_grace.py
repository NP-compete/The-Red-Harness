"""Shutdown finishes before SIGKILL (REL-2)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
OVERLAYS = ROOT / "deployment" / "overlays"

from agent.aegra.shutdown import (  # noqa: E402
    SHUTDOWN_DRAIN_SECONDS,
    SHUTDOWN_LANGFUSE_TIMEOUT_SECONDS,
)

TELEMETRY_FLUSH_SECONDS = 15
assert TELEMETRY_FLUSH_SECONDS >= SHUTDOWN_LANGFUSE_TIMEOUT_SECONDS

HEADROOM_SECONDS = 5


def _rendered(overlay: str) -> list[dict]:
    try:
        out = subprocess.run(
            ["kubectl", "kustomize", str(OVERLAYS / overlay)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:  # pragma: no cover - needs kubectl
        # The guard below only caught "kubectl ran and failed". With no
        # kubectl at all this raised instead, so the suite errored
        # rather than skipping the moment it ran anywhere without it.
        pytest.skip("kubectl is not installed")
    if out.returncode != 0:  # pragma: no cover - needs kubectl
        pytest.skip(f"kubectl kustomize {overlay} failed: {out.stderr[:200]}")
    return [doc for doc in yaml.safe_load_all(out.stdout) if doc]


OURS = ("agent", "eval-worker")


def _workloads(overlay: str):
    """Every pod template that runs the agent's shutdown path."""
    found = []
    for doc in _rendered(overlay):
        if doc.get("kind") not in ("Deployment", "StatefulSet"):
            continue
        spec = doc["spec"]["template"]["spec"]
        for container in spec.get("containers", []):
            if container["name"] not in OURS:
                continue
            sleep = 0
            stop = (container.get("lifecycle") or {}).get("preStop") or {}
            command = (stop.get("exec") or {}).get("command") or []
            if len(command) == 2 and command[0] == "sleep":
                sleep = int(command[1])
            own = None
            for entry in container.get("env") or []:
                if entry.get("name") == "SHUTDOWN_GRACE_PERIOD_SECONDS":
                    own = entry.get("value")
            found.append(
                (
                    f"{overlay}/{doc['metadata']['name']}/{container['name']}",
                    int(spec.get("terminationGracePeriodSeconds", 30)),
                    sleep,
                    own,
                )
            )
    return found


def _tuning(overlay: str) -> dict[str, str]:
    for doc in _rendered(overlay):
        if doc.get("kind") == "ConfigMap" and doc["metadata"]["name"] == "agent-tuning":
            return doc.get("data") or {}
    return {}


@pytest.mark.parametrize("overlay", ["kind", "openshift"])
class TestTheProcessKnowsItsOwnBudget:
    """`shutdown.py` warns when it has no headroom — if it is told."""

    def test_it_is_set_at_all(self, overlay):
        assert "SHUTDOWN_GRACE_PERIOD_SECONDS" in _tuning(overlay), (
            "nothing sets it, so the shutdown headroom warning is comparing "
            "against a default of 60 that no pod necessarily has"
        )

    def test_it_is_the_grace_the_process_actually_gets(self, overlay):
        """Per container, because they do not all have the same one."""
        shared = _tuning(overlay).get("SHUTDOWN_GRACE_PERIOD_SECONDS")
        for where, grace, sleep, own in _workloads(overlay):
            told = int(own if own is not None else shared)
            assert told == grace - sleep, (
                f"{where} has {grace}s grace and a {sleep}s preStop, so the "
                f"process gets {grace - sleep}s — but it is told {told}s"
            )


@pytest.mark.parametrize("overlay", ["kind", "openshift"])
class TestEveryWorkloadHasRoomToShutDown:
    def test_the_budget_fits(self, overlay):
        needed = SHUTDOWN_DRAIN_SECONDS + TELEMETRY_FLUSH_SECONDS + HEADROOM_SECONDS
        tight = [
            f"{where}: {grace}s grace − {sleep}s preStop = {grace - sleep}s for a "
            f"shutdown that needs {needed}s"
            for where, grace, sleep, _ in _workloads(overlay)
            if grace - sleep < needed
        ]
        assert not tight, (
            "the kubelet starts the grace clock before preStop, so those "
            "seconds come out of the same budget:\n  " + "\n  ".join(tight)
        )

    def test_the_agent_itself_is_among_them(self, overlay):
        """A loop over an empty list passes (pattern 5)."""
        assert any(where.endswith("/agent") for where, *_ in _workloads(overlay)), (
            f"{overlay} rendered no agent container; this check saw nothing"
        )
