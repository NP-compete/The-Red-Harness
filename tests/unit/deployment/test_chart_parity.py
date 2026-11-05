"""Two renderers, one input — and something that checks they agree."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest
import yaml

from scripts.deploy.render_deployment import REPO_ROOT

CHART = REPO_ROOT / "deployment" / "chart"
VALUES = yaml.safe_load(
    (REPO_ROOT / "config" / "agent" / "deployment" / "values.yaml").read_text()
)

helm = pytest.mark.skipif(shutil.which("helm") is None, reason="helm is not installed")


def _run(*args: str) -> str:
    return subprocess.run(
        ["helm", *args],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    ).stdout


@pytest.fixture(scope="module")
def rendered() -> dict[str, dict]:
    """Every object the chart produces, keyed by kind and name."""
    out = _run("template", "agent", str(CHART))
    return {
        f"{d['kind']}/{d['metadata']['name']}": d for d in yaml.safe_load_all(out) if d
    }


@pytest.fixture(scope="module")
def container(rendered: dict[str, dict]) -> dict:
    deployment = rendered["Deployment/agent"]
    return deployment["spec"]["template"]["spec"]["containers"][0]


class TestTheChartIsAChart:
    def test_it_has_a_chart_file(self):
        assert (CHART / "Chart.yaml").is_file()

    def test_it_declares_a_values_schema(self):
        assert (CHART / "values.schema.json").is_file()

    @helm
    def test_it_lints(self):
        assert "0 chart(s) failed" in _run("lint", str(CHART))


class TestItAgreesWithTheOverlay:
    """The fields an operator would notice getting this wrong."""

    @helm
    def test_the_image_is_the_one_values_names(self, container):
        assert VALUES["image"]["name"] in container["image"]
        assert VALUES["image"]["tag"] in container["image"]

    @helm
    def test_the_port_matches(self, container):
        assert container["ports"][0]["containerPort"] == VALUES["container"]["port"]

    @helm
    def test_the_resources_match(self, container):
        assert container["resources"] == {
            "requests": VALUES["resources"]["requests"],
            "limits": VALUES["resources"]["limits"],
        }

    @helm
    @pytest.mark.parametrize("probe", ["liveness", "readiness", "startup"])
    def test_each_probe_matches(self, container, probe):
        want = VALUES["probes"][probe]
        got = container[f"{probe}Probe"]
        assert got["httpGet"]["path"] == want["path"]
        assert got["periodSeconds"] == want["periodSeconds"]
        assert got["failureThreshold"] == want["failureThreshold"]

    @helm
    def test_the_replica_count_matches(self, rendered):
        assert (
            rendered["Deployment/agent"]["spec"]["replicas"]
            == VALUES["app"]["replicas"]
        )

    @helm
    def test_the_rollout_matches(self, rendered):
        spec = rendered["Deployment/agent"]["spec"]
        rolling = spec["strategy"]["rollingUpdate"]
        assert rolling["maxSurge"] == VALUES["rollout"]["maxSurge"]
        assert rolling["maxUnavailable"] == VALUES["rollout"]["maxUnavailable"]
        assert spec["minReadySeconds"] == VALUES["rollout"]["minReadySeconds"]

    @helm
    def test_the_drain_window_matches(self, rendered):
        spec = rendered["Deployment/agent"]["spec"]["template"]["spec"]
        assert (
            spec["terminationGracePeriodSeconds"]
            == VALUES["drain"]["terminationGracePeriodSeconds"]
        )


class TestItSatisfiesTheClusterItDeploysTo:
    """Restricted SCC refuses a pod that gets any of these wrong."""

    @helm
    def test_the_container_does_not_run_as_root(self, container):
        assert container["securityContext"]["runAsNonRoot"] is True

    @helm
    def test_it_cannot_escalate_privileges(self, container):
        assert container["securityContext"]["allowPrivilegeEscalation"] is False

    @helm
    def test_it_drops_every_capability(self, container):
        assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]

    @helm
    def test_it_asks_for_no_uid_of_its_own(self, container):
        assert "runAsUser" not in container["securityContext"]


class TestWhatItDeploys:
    @helm
    def test_a_service_on_the_configured_port(self, rendered):
        service = rendered["Service/agent"]
        assert (
            service["spec"]["ports"][0]["port"]
            == VALUES["networking"]["service"]["port"]
        )

    @helm
    def test_a_route_when_one_is_asked_for(self, rendered):
        assert "Route/agent" in rendered

    @helm
    def test_the_route_terminates_tls_as_configured(self, rendered):
        tls = rendered["Route/agent"]["spec"]["tls"]
        assert tls["termination"] == VALUES["networking"]["route"]["tls"]["termination"]


class TestTheSchemaDescribesTheRealValues:
    def test_every_top_level_section_is_known_to_the_schema(self):
        schema = json.loads((CHART / "values.schema.json").read_text())
        assert set(VALUES) <= set(schema["properties"])


class TestTheChartCannotDriftQuietly:
    """`plan()` owns the chart's inputs, so the drift check sees them."""

    def test_the_renderer_writes_the_charts_values(self):
        from scripts.deploy.render_deployment import plan

        assert CHART / "values.yaml" in plan(VALUES)

    def test_the_renderer_writes_the_charts_schema(self):
        from scripts.deploy.render_deployment import plan

        assert CHART / "values.schema.json" in plan(VALUES)

    def test_what_is_committed_is_what_the_renderer_would_write(self):
        from scripts.deploy.render_deployment import plan

        wanted = plan(VALUES)
        for path in (CHART / "values.yaml", CHART / "values.schema.json"):
            assert path.read_text() == wanted[path], f"{path.name} has drifted"

    def test_a_changed_value_reaches_the_chart(self):
        from scripts.deploy.render_deployment import plan

        changed = yaml.safe_load(yaml.safe_dump(VALUES))
        changed["resources"]["limits"]["memory"] = "8Gi"
        assert "8Gi" in plan(changed)[CHART / "values.yaml"]


COMPONENTS = REPO_ROOT / "deployment" / "components"


def _component(name: str) -> dict:
    return yaml.safe_load((COMPONENTS / name / "pvc.yaml").read_text())


class TestTheConfigAndSecretsTravelWithIt:
    """An install from the chart alone has to bring its own config."""

    @helm
    def test_it_ships_the_config_map_the_pod_reads(self, rendered):
        assert "ConfigMap/agent-config" in rendered

    @helm
    def test_the_config_map_carries_what_values_declares(self, rendered):
        data = rendered["ConfigMap/agent-config"]["data"]
        for key, value in VALUES["config"].items():
            assert data[key] == str(value)

    @helm
    def test_it_ships_the_secret_the_pod_reads(self, rendered):
        assert "Secret/agent-secrets" in rendered

    @helm
    def test_the_secret_ships_no_credential_of_its_own(self, rendered):
        values = rendered["Secret/agent-secrets"].get("stringData", {})
        assert values, "the pod reads these by name; the keys have to exist"
        assert all(
            value == "" or value.startswith("<path:") for value in values.values()
        )


class TestTheVolumesMatchTheComponents:
    """The same claims kustomize makes, or the two installs differ."""

    @helm
    def test_it_claims_space_for_documents(self, rendered):
        assert "PersistentVolumeClaim/agent-documents-pvc" in rendered

    @helm
    def test_the_documents_claim_is_the_size_kustomize_asks_for(self, rendered):
        want = _component("documents-pvc")["spec"]["resources"]["requests"]["storage"]
        got = rendered["PersistentVolumeClaim/agent-documents-pvc"]["spec"]
        assert got["resources"]["requests"]["storage"] == want

    @helm
    def test_the_documents_claim_can_be_mounted_by_every_replica(self, rendered):
        got = rendered["PersistentVolumeClaim/agent-documents-pvc"]["spec"]
        assert got["accessModes"] == ["ReadWriteMany"]

    @helm
    def test_it_claims_space_for_config(self, rendered):
        assert "PersistentVolumeClaim/config-pvc" in rendered

    @helm
    def test_the_config_claim_is_the_size_kustomize_asks_for(self, rendered):
        want = _component("config-pvc")["spec"]["resources"]["requests"]["storage"]
        got = rendered["PersistentVolumeClaim/config-pvc"]["spec"]
        assert got["resources"]["requests"]["storage"] == want

    @helm
    def test_a_claim_nobody_asked_for_is_not_made(self):
        out = _run(
            "template", "agent", str(CHART), "--set", "components.documentsPvc=false"
        )
        assert "agent-documents-pvc" not in out


class TestScaleToZeroIsAToggle:
    """The same objects the kustomize component produces."""

    def _rendered(self, *overrides: str) -> dict[str, dict]:
        out = _run("template", "agent", str(CHART), *overrides)
        return {
            f"{d['kind']}/{d['metadata']['name']}": d
            for d in yaml.safe_load_all(out)
            if d
        }

    @helm
    def test_off_by_default(self, rendered):
        assert not [k for k in rendered if k.startswith("ScaledObject/")]

    @helm
    def test_turning_it_on_produces_the_scaled_object(self):
        found = self._rendered("--set", "components.scaleToZero=true")
        assert "ScaledObject/agent" in found

    @helm
    def test_it_scales_to_nothing_when_nothing_is_in_flight(self):
        found = self._rendered("--set", "components.scaleToZero=true")
        assert found["ScaledObject/agent"]["spec"]["minReplicaCount"] == 0

    @helm
    def test_the_deployment_stops_naming_a_replica_count(self):
        found = self._rendered("--set", "components.scaleToZero=true")
        assert "replicas" not in found["Deployment/agent"]["spec"]

    @helm
    def test_autoscaling_and_scale_to_zero_are_not_both_installed(self):
        found = self._rendered("--set", "components.scaleToZero=true")
        assert not [k for k in found if k.startswith("HorizontalPodAutoscaler/")]


class TestItTellsAnOperatorHowToInstallIt:
    def test_there_is_deployment_documentation(self):
        assert (REPO_ROOT / "deployment" / "README.md").is_file()

    def test_it_says_how_to_install_the_chart(self):
        said = (REPO_ROOT / "deployment" / "README.md").read_text()
        assert "helm install" in said

    def test_it_says_how_to_see_what_would_be_installed(self):
        said = (REPO_ROOT / "deployment" / "README.md").read_text()
        assert "helm template" in said
