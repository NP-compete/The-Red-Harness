"""A patch may not quietly take a volume away (DEP-5)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
OVERLAYS = ("kind", "openshift")


def _render(overlay: str) -> list[dict]:
    out = subprocess.run(
        ["kubectl", "kustomize", f"deployment/overlays/{overlay}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr[:2000]
    return [d for d in yaml.safe_load_all(out.stdout) if isinstance(d, dict)]


def _pod_specs(docs: list[dict]) -> dict[str, dict]:
    found = {}
    for doc in docs:
        if doc.get("kind") in ("Deployment", "StatefulSet", "Job"):
            found[doc["metadata"]["name"]] = doc["spec"]["template"]["spec"]
    return found


def _declared_in_sources(overlay: str) -> dict[str, set[str]]:
    """Volumes named by a deployment in the components or *this* overlay."""
    found: dict[str, set[str]] = {}
    for path in sorted(ROOT.glob("deployment/components/**/*.yaml")) + sorted(
        ROOT.glob(f"deployment/overlays/{overlay}/*.yaml")
    ):
        for doc in yaml.safe_load_all(path.read_text()):
            if not isinstance(doc, dict) or doc.get("kind") != "Deployment":
                continue
            spec = (doc.get("spec") or {}).get("template", {}).get("spec") or {}
            names = {v["name"] for v in (spec.get("volumes") or []) if "name" in v}
            if names:
                found.setdefault(doc["metadata"]["name"], set()).update(names)
    return found


@pytest.mark.parametrize("overlay", OVERLAYS)
class TestEveryMountHasAVolume:
    def test_the_overlay_renders_workloads(self, overlay: str):
        assert len(_pod_specs(_render(overlay))) >= 2

    def test_no_mount_points_at_a_volume_that_is_gone(self, overlay: str):
        for name, spec in _pod_specs(_render(overlay)).items():
            declared = {v["name"] for v in (spec.get("volumes") or [])}
            containers = (spec.get("containers") or []) + (
                spec.get("initContainers") or []
            )
            for container in containers:
                for mount in container.get("volumeMounts") or []:
                    assert mount["name"] in declared, (
                        f"{overlay}/{name}/{container['name']} mounts "
                        f"{mount['name']!r} and the pod declares no such volume. "
                        "A patch replaced the volumes array instead of merging "
                        "into it (DEP-5); the cluster would refuse this pod."
                    )


@pytest.mark.parametrize("overlay", OVERLAYS)
class TestNothingDeclaredIsLost:
    def test_the_render_keeps_every_source_volume(self, overlay: str):
        rendered = _pod_specs(_render(overlay))
        sources = _declared_in_sources(overlay)
        checked = 0
        for name, spec in rendered.items():
            if name not in sources:
                continue
            have = {v["name"] for v in (spec.get("volumes") or [])}
            checked += 1
            missing = sources[name] - have
            assert not missing, (
                f"{overlay}/{name} lost {sorted(missing)} between its source "
                "and the render — a patch replaced the array rather than "
                "merging by name (DEP-5)"
            )
        assert checked, f"no workload in {overlay} was compared against a source"
