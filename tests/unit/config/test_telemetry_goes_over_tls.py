"""Telemetry goes over TLS unless a deployment says otherwise (OBS-2)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]

MAY_BE_PLAINTEXT = {
    "kind": "a local collector with no TLS",
    "openshift": "a cluster-internal collector on the pod network",
}


class TestTheModel:
    def test_the_exporter_defaults_to_tls(self):
        from agent.src.agent.config.otel import OtelExporterConfig

        assert OtelExporterConfig().insecure is False


class TestTheShippedTree:
    def test_observability_yaml_asks_for_tls(self):
        raw = yaml.safe_load(
            (ROOT / "config/agent/runtime/observability.yaml").read_text()
        )
        assert raw["otel"]["exporter"]["insecure"] is False


class TestTheDeployment:
    def test_the_base_configmap_asks_for_tls(self):
        """The one that actually reaches a cluster."""
        raw = yaml.safe_load((ROOT / "deployment/base/configmap.yaml").read_text())
        assert raw["data"]["OTEL_EXPORTER_OTLP_INSECURE"] == "false"

    @pytest.mark.parametrize("overlay", sorted(MAY_BE_PLAINTEXT))
    def test_an_overlay_that_wants_plaintext_says_so(self, overlay):
        patch = ROOT / f"deployment/overlays/{overlay}/configmap-patch.yaml"
        if not patch.is_file():  # pragma: no cover - overlay without a patch
            pytest.skip(f"{overlay} has no configmap patch")
        raw = yaml.safe_load(patch.read_text()) or {}
        said = (raw.get("data") or {}).get("OTEL_EXPORTER_OTLP_INSECURE")
        assert said == "true", (
            f"{overlay} is listed as allowed to send plaintext ("
            f"{MAY_BE_PLAINTEXT[overlay]}) and does not say so in its own "
            "patch. Either it uses TLS now — remove it from the list — or "
            "it is relying on a default that no longer exists."
        )

    def test_no_other_overlay_sends_plaintext(self):
        """The direction that rots: a new overlay inheriting a yes."""
        overlays = ROOT / "deployment/overlays"
        offenders = []
        for patch in sorted(overlays.glob("*/configmap-patch.yaml")):
            name = patch.parent.name
            raw = yaml.safe_load(patch.read_text()) or {}
            said = (raw.get("data") or {}).get("OTEL_EXPORTER_OTLP_INSECURE")
            if said == "true" and name not in MAY_BE_PLAINTEXT:
                offenders.append(name)
        assert offenders == [], offenders
