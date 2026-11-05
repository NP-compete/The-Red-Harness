"""OpenShift constraints, enforced against rendered manifests."""

from __future__ import annotations

import pytest

from tests.fixtures.manifests import (
    all_containers,
    kustomize_available,
    of_kind,
    pod_specs,
    render,
)

pytestmark = pytest.mark.skipif(
    not kustomize_available(), reason="needs kubectl or kustomize on PATH"
)


@pytest.fixture(scope="module")
def openshift():
    return render("openshift")


class TestOverlaysRender:
    @pytest.mark.parametrize("overlay", ["openshift", "kind"])
    def test_overlay_renders(self, overlay: str):
        """A broken overlay should fail in CI, not at deploy time."""
        assert render(overlay), f"{overlay} rendered no manifests"


class TestRestrictedSCC:
    """Restricted SCC: no privileged containers, no root, no escalation."""

    def test_no_container_is_privileged(self, openshift):
        for name, spec in pod_specs(openshift):
            for container in all_containers(spec):
                security = container.get("securityContext") or {}
                assert not security.get("privileged"), (
                    f"{name}/{container['name']} requests privileged"
                )

    def test_no_privilege_escalation(self, openshift):
        for name, spec in pod_specs(openshift):
            for container in all_containers(spec):
                security = container.get("securityContext") or {}
                assert security.get("allowPrivilegeEscalation") is not True, (
                    f"{name}/{container['name']} allows privilege escalation"
                )

    def test_no_hardcoded_runasuser(self, openshift):
        """OpenShift assigns an arbitrary UID from the namespace range."""
        for name, spec in pod_specs(openshift):
            pod_security = spec.get("securityContext") or {}
            assert "runAsUser" not in pod_security, f"{name} pins runAsUser"
            for container in all_containers(spec):
                security = container.get("securityContext") or {}
                assert "runAsUser" not in security, (
                    f"{name}/{container['name']} pins runAsUser"
                )

    def test_no_host_namespaces_or_host_path(self, openshift):
        for name, spec in pod_specs(openshift):
            for field in ("hostNetwork", "hostPID", "hostIPC"):
                assert not spec.get(field), f"{name} requests {field}"
            for volume in spec.get("volumes") or []:
                assert "hostPath" not in volume, f"{name} mounts a hostPath"


class TestResourceGovernance:
    def test_every_container_declares_resources(self, openshift):
        """Without limits a pod is BestEffort and evicted first."""
        for name, spec in pod_specs(openshift):
            for container in all_containers(spec):
                resources = container.get("resources") or {}
                assert resources.get("requests"), (
                    f"{name}/{container['name']} has no resource requests"
                )
                assert resources.get("limits"), (
                    f"{name}/{container['name']} has no resource limits"
                )


class TestIngressIsARoute:
    """DEP-3: a Route in preprod and prod; nginx only in Kind."""

    def test_ingress_is_a_route_in_openshift(self, openshift):
        routes = of_kind(openshift, "Route")
        assert routes, (
            "the OpenShift overlay renders no Route. Ingress there is a "
            "Route; an nginx Ingress is the Kind overlay's business."
        )

    def test_nginx_is_kind_only(self):
        """And the other half, which is the one that rots."""
        shipped = of_kind(render("openshift"), "Ingress")
        assert not shipped, (
            f"the OpenShift overlay renders {len(shipped)} Ingress object(s). "
            "nginx is not in the production path."
        )
        assert of_kind(render("kind"), "Ingress"), (
            "the Kind overlay renders no Ingress — it is how the local "
            "cluster is reached at all"
        )


class TestConfigIsReadOnly:
    """DEP-6: a pod never writes back to its own ConfigMap."""

    @pytest.mark.parametrize("overlay", ["openshift", "kind"])
    def test_the_config_volume_is_mounted_read_only(self, overlay: str):
        """Every ConfigMap-backed mount, in both overlays."""
        rendered = render(overlay)
        writable = []
        for workload, spec in pod_specs(rendered):
            from_config_map = {
                volume.get("name")
                for volume in (spec.get("volumes") or [])
                if "configMap" in volume
            }
            for container in all_containers(spec):
                for mount in container.get("volumeMounts") or []:
                    if mount.get("name") in from_config_map and not mount.get(
                        "readOnly"
                    ):
                        writable.append(
                            f"{workload}/{container.get('name')}"
                            f":{mount.get('mountPath')}"
                        )

        assert not writable, (
            f"these ConfigMap mounts are writable: {writable}. A pod that "
            "can write to its own configuration can disagree with the "
            "ConfigMap it started from, and the next restart silently "
            "undoes whatever it wrote."
        )


class TestStreamingSurvivesTheRouter:
    def test_routes_raise_the_haproxy_idle_timeout(self, openshift):
        """HAProxy defaults to 30s, which severs SSE during a long turn."""
        routes = of_kind(openshift, "Route")
        assert routes, "no Route rendered"

        for route in routes:
            annotations = (route.get("metadata") or {}).get("annotations") or {}
            timeout = annotations.get("haproxy.router.openshift.io/timeout")
            assert timeout, (
                f"Route/{route['metadata']['name']} has no timeout annotation; "
                "SSE will be cut at the 30s default"
            )


class TestMultiPodSafety:
    """Several replicas behind an HPA, so nothing may assume singleton."""

    def test_migrations_do_not_run_on_every_replica(self, openshift):
        """Every replica racing Alembic's lock restart-loops the rollout."""
        deployments = {
            d["metadata"]["name"]: d for d in of_kind(openshift, "Deployment")
        }
        agent = deployments.get("agent")
        assert agent is not None

        replicas = agent["spec"].get("replicas", 1)
        if replicas <= 1:
            pytest.skip("single replica; no migration race")

        configmaps = {
            c["metadata"]["name"]: (c.get("data") or {})
            for c in of_kind(openshift, "ConfigMap")
        }
        flag = configmaps.get("agent-config", {}).get("RUN_MIGRATIONS_ON_STARTUP")

        assert flag == "false", (
            f"agent runs {replicas} replicas but RUN_MIGRATIONS_ON_STARTUP={flag!r}; "
            "migrations must run out-of-band (see the db-migrate init container)"
        )

    def test_a_migration_init_container_exists(self, openshift):
        """If startup migrations are off, something must still run them."""
        agent = next(
            d
            for d in of_kind(openshift, "Deployment")
            if d["metadata"]["name"] == "agent"
        )
        init = (agent["spec"]["template"]["spec"].get("initContainers")) or []

        assert any("migrate" in c["name"] for c in init), (
            "no migration init container; schema would never be upgraded"
        )

    def test_pdb_allows_voluntary_disruption(self, openshift):
        """A PDB that permits zero disruption blocks every node drain."""
        for pdb in of_kind(openshift, "PodDisruptionBudget"):
            spec = pdb.get("spec") or {}
            name = pdb["metadata"]["name"]

            deployments = {
                d["metadata"]["name"]: d.get("spec", {}).get("replicas", 1)
                for d in of_kind(openshift, "Deployment")
            }
            replicas = deployments.get(name, 1)

            if "minAvailable" in spec and isinstance(spec["minAvailable"], int):
                assert spec["minAvailable"] < replicas, (
                    f"PDB/{name} minAvailable={spec['minAvailable']} with "
                    f"{replicas} replicas blocks all voluntary eviction"
                )


class TestCrashRecoveryIsActuallyOn:
    """The Redis worker queue, without which crash recovery is a no-op."""

    @pytest.mark.parametrize("overlay", ["kind", "openshift"])
    def test_the_broker_is_enabled(self, overlay: str):
        configmaps = {
            c["metadata"]["name"]: (c.get("data") or {})
            for c in of_kind(render(overlay), "ConfigMap")
        }
        flag = configmaps.get("agent-config", {}).get("REDIS_BROKER_ENABLED")

        assert flag == "true", (
            f"{overlay}: REDIS_BROKER_ENABLED={flag!r}; runs would take no "
            "lease and the LeaseReaper could not recover them"
        )

    @pytest.mark.parametrize("overlay", ["kind", "openshift"])
    def test_the_agent_container_actually_receives_it(self, overlay: str):
        """A ConfigMap key is not configuration until a container reads it."""
        agent = next(
            d
            for d in of_kind(render(overlay), "Deployment")
            if d["metadata"]["name"] == "agent"
        )
        container = next(
            c
            for c in agent["spec"]["template"]["spec"]["containers"]
            if c["name"] == "agent"
        )

        from_env_from = any(
            (source.get("configMapRef") or {}).get("name") == "agent-config"
            for source in container.get("envFrom") or []
        )
        named = any(
            e["name"] == "REDIS_BROKER_ENABLED" for e in container.get("env") or []
        )

        assert from_env_from or named, (
            f"{overlay}: agent container reads neither the whole agent-config "
            "nor REDIS_BROKER_ENABLED by name; the flag never reaches Aegra"
        )


class TestExternalChannelsComponent:
    """The only Route in this repo that faces the internet."""

    @pytest.fixture(scope="class")
    def rendered(self, tmp_path_factory):
        import shutil
        import subprocess

        import yaml as _yaml

        from scripts.deploy import render_deployment
        from tests.fixtures.manifests import REPO

        work = tmp_path_factory.mktemp("channels")
        shutil.copytree(REPO / "deployment", work / "deployment")

        values = _yaml.safe_load(
            (REPO / "config" / "agent" / "deployment" / "values.yaml").read_text()
        )
        values["components"]["externalChannels"] = True

        overlay = work / "deployment" / "overlays" / "openshift"
        resolved = render_deployment.for_target(values, "openshift")
        (overlay / "generated.yaml").write_text(
            render_deployment.render_patches(resolved, "openshift")
        )
        kustomization = overlay / "kustomization.yaml"
        kustomization.write_text(
            render_deployment.rewrite_components(
                kustomization.read_text(),
                render_deployment.render_components(resolved),
            )
        )

        result = subprocess.run(
            ["kubectl", "kustomize", str(overlay)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        return tuple(d for d in _yaml.safe_load_all(result.stdout) if d)

    def _external(self, rendered):
        routes = [
            r
            for r in of_kind(rendered, "Route")
            if r["metadata"].get("labels", {}).get("shard") == "external"
        ]
        assert len(routes) == 1, "expected exactly one external Route"
        return routes[0]

    def test_the_external_route_exposes_only_channels(self, rendered):
        """Without a path, /threads and /admin would be public too."""
        assert self._external(rendered)["spec"].get("path") == "/channels"

    def test_the_main_agent_route_stays_internal(self, rendered):
        """Enabling channels must not widen the existing Route."""
        main = [
            r for r in of_kind(rendered, "Route") if r["metadata"]["name"] == "agent"
        ]
        assert main, "the main agent Route disappeared"
        assert main[0]["metadata"]["labels"]["shard"] == "internal"
        assert "path" not in main[0]["spec"] or main[0]["spec"]["path"] == "/"

    def test_the_external_route_terminates_tls(self, rendered):
        route = self._external(rendered)
        assert route["spec"]["tls"]["termination"] == "edge"
        assert route["spec"]["tls"]["insecureEdgeTerminationPolicy"] == "Redirect"

    def test_the_external_route_is_rate_limited(self, rendered):
        """Anyone who learns the hostname can reach it."""
        annotations = self._external(rendered)["metadata"]["annotations"]
        assert (
            annotations.get("haproxy.router.openshift.io/rate-limit-connections")
            == "true"
        )

    def test_the_external_route_does_not_inherit_the_streaming_timeout(self, rendered):
        """Channels ack in milliseconds; 5 hours is an idle-socket budget."""
        timeout = self._external(rendered)["metadata"]["annotations"][
            "haproxy.router.openshift.io/timeout"
        ]
        assert timeout.endswith("s")
        assert int(timeout.rstrip("s")) <= 120

    def test_a_networkpolicy_admits_the_ingress_controller(self, rendered):
        """Otherwise the Route resolves and then times out."""
        policies = of_kind(rendered, "NetworkPolicy")
        assert any(
            "ingress" in str(p.get("spec", {}).get("ingress", "")) for p in policies
        ), "no NetworkPolicy admits ingress traffic to the agent"


class TestChannelsAreOffByDefault:
    def test_no_external_route_is_rendered_normally(self, openshift):
        """The component is opt-in; the default render must stay internal."""
        shards = {
            r["metadata"].get("labels", {}).get("shard")
            for r in of_kind(openshift, "Route")
        }
        assert "external" not in shards


class TestSecrets:
    def test_no_literal_credentials_in_rendered_output(self, openshift):
        """Secrets belong in Secret objects, not baked into env values."""
        suspicious = ("BEGIN PRIVATE KEY", "xoxb-", "sk-live", "AKIA")

        for manifest in openshift:
            if manifest.get("kind") == "Secret":
                continue
            body = str(manifest)
            for needle in suspicious:
                assert needle not in body, (
                    f"{manifest.get('kind')}/"
                    f"{(manifest.get('metadata') or {}).get('name')} "
                    f"contains {needle!r}"
                )

    def test_secret_values_are_placeholders_not_real(self, openshift):
        """The template ships a Secret skeleton; real values come from the"""
        import base64

        for secret in of_kind(openshift, "Secret"):
            for key, value in (secret.get("data") or {}).items():
                decoded = base64.b64decode(value).decode(errors="replace")
                assert len(decoded) < 200, (
                    f"Secret/{secret['metadata']['name']}.{key} looks like a "
                    "real credential rather than a placeholder"
                )


class TestScaleToZeroComponent:
    """The opt-in scale-to-zero component (`components/scale-to-zero`)."""

    @pytest.fixture(scope="class")
    def rendered(self, tmp_path_factory):
        import shutil
        import subprocess

        from tests.fixtures.manifests import REPO

        work = tmp_path_factory.mktemp("s2z")
        shutil.copytree(REPO / "deployment", work / "deployment")

        import yaml as _yaml

        from scripts.deploy import render_deployment

        values = _yaml.safe_load(
            (REPO / "config" / "agent" / "deployment" / "values.yaml").read_text()
        )
        values["components"]["scaleToZero"] = True
        values["autoscaling"]["enabled"] = False

        overlay = work / "deployment" / "overlays" / "openshift"
        resolved = render_deployment.for_target(values, "openshift")
        (overlay / "generated.yaml").write_text(
            render_deployment.render_patches(resolved, "openshift")
        )
        kustomization = overlay / "kustomization.yaml"
        kustomization.write_text(
            render_deployment.rewrite_components(
                kustomization.read_text(),
                render_deployment.render_components(resolved),
            )
        )

        result = subprocess.run(
            ["kubectl", "kustomize", str(kustomization.parent)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr

        import yaml

        return tuple(d for d in yaml.safe_load_all(result.stdout) if d)

    def test_component_is_not_enabled_by_default(self, openshift):
        """Scale-to-zero costs a cold start and stops cron; opt in only."""
        assert not of_kind(openshift, "HTTPScaledObject")

    def test_enabling_it_sets_the_agent_to_zero_replicas(self, rendered):
        agent = next(
            d
            for d in of_kind(rendered, "Deployment")
            if d["metadata"]["name"] == "agent"
        )
        assert agent["spec"]["replicas"] == 0

    def test_enabling_it_removes_the_conflicting_hpa(self, rendered):
        """Two autoscalers on one Deployment oscillate the replica count."""
        names = [
            h["metadata"]["name"] for h in of_kind(rendered, "HorizontalPodAutoscaler")
        ]
        assert "agent" not in names

    def test_route_targets_the_interceptor(self, rendered):
        """At zero replicas the agent Service answers 503 and never wakes."""
        route = next(
            r for r in of_kind(rendered, "Route") if r["metadata"]["name"] == "agent"
        )
        assert "interceptor" in route["spec"]["to"]["name"]

    def test_both_triggers_live_in_one_scaledobject(self, rendered):
        """Two autoscalers on one Deployment oscillate the replica count."""
        from tests.fixtures.manifests import of_kind as _of_kind

        scalers = _of_kind(rendered, "ScaledObject")
        assert len(scalers) == 1

        https = _of_kind(rendered, "HTTPScaledObject")
        assert len(https) == 1, "the interceptor needs its routing entry"
        annotations = https[0]["metadata"].get("annotations") or {}
        assert (
            annotations.get("httpscaledobject.keda.sh/skip-scaledobject-creation")
            == "true"
        ), "without this the add-on adds a second scaler on the same Deployment"

        triggers = {t["type"] for t in scalers[0]["spec"]["triggers"]}
        assert "external" in triggers, "nothing wakes the pod from zero"
        assert "prometheus" in triggers, "nothing protects in-flight runs"

    def test_in_flight_metric_blocks_scale_to_zero(self, rendered):
        """activationThreshold 0 means any in-flight run holds a replica."""
        from tests.fixtures.manifests import of_kind as _of_kind

        scaler = _of_kind(rendered, "ScaledObject")[0]
        prom = next(t for t in scaler["spec"]["triggers"] if t["type"] == "prometheus")

        assert prom["metadata"]["activationThreshold"] == "0"
        assert "aegra_runs_in_flight" in prom["metadata"]["query"]

    def test_in_flight_query_does_not_sum_a_clusterwide_gauge(self, rendered):
        """Every replica reports the same cluster-wide value, so summing"""
        from tests.fixtures.manifests import of_kind as _of_kind

        scaler = _of_kind(rendered, "ScaledObject")[0]
        prom = next(t for t in scaler["spec"]["triggers"] if t["type"] == "prometheus")

        assert prom["metadata"]["query"].startswith("max(")

    def test_a_wakeup_cronjob_keeps_scheduled_work_firing(self, rendered):
        """Aegra's scheduler catches up on overdue crons, but only while a"""
        from tests.fixtures.manifests import of_kind as _of_kind

        cronjobs = _of_kind(rendered, "CronJob")
        assert any("wakeup" in c["metadata"]["name"] for c in cronjobs), (
            "scale-to-zero without a wake-up means cron silently stops"
        )

    def test_wakeup_timeout_outlasts_a_cold_start(self, rendered):
        """A poke that gives up before the pod is Ready wakes nothing."""
        from tests.fixtures.manifests import of_kind as _of_kind

        cronjob = next(
            c
            for c in _of_kind(rendered, "CronJob")
            if "wakeup" in c["metadata"]["name"]
        )
        container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"][
            "containers"
        ][0]
        command = " ".join(container["command"])

        assert "--max-time" in command
        timeout = int(command.split("--max-time")[1].split()[0])
        assert timeout >= 90, f"--max-time {timeout}s is shorter than a cold start"


class TestMetricsAreCollected:
    """Publishing metrics nothing scrapes makes the autoscaler read an"""

    def test_prometheus_metrics_are_enabled_by_default(self, openshift):
        configmaps = {
            c["metadata"]["name"]: (c.get("data") or {})
            for c in of_kind(openshift, "ConfigMap")
        }
        assert configmaps["agent-config"]["ENABLE_PROMETHEUS_METRICS"] == "true"

    def test_the_flag_reaches_the_container(self, openshift):
        """A configmap key nothing references changes nothing."""
        agent = next(
            d
            for d in of_kind(openshift, "Deployment")
            if d["metadata"]["name"] == "agent"
        )
        container = agent["spec"]["template"]["spec"]["containers"][0]
        names = {e["name"] for e in container.get("env") or []}

        assert "ENABLE_PROMETHEUS_METRICS" in names

    def test_a_servicemonitor_scrapes_the_agent(self, openshift):
        monitors = of_kind(openshift, "ServiceMonitor")
        assert monitors, "metrics are published but nothing collects them"

        endpoint = monitors[0]["spec"]["endpoints"][0]
        assert endpoint["path"] == "/metrics"

    def test_scrape_interval_keeps_pace_with_the_scaler(self, openshift):
        """KEDA polls every 15s; a slower scrape makes it decide on data"""
        monitor = of_kind(openshift, "ServiceMonitor")[0]
        interval = monitor["spec"]["endpoints"][0]["interval"]

        assert interval.endswith("s")
        assert int(interval.rstrip("s")) <= 15

    def test_servicemonitor_selector_matches_the_service(self, openshift):
        """A selector that matches nothing fails silently."""
        monitor = of_kind(openshift, "ServiceMonitor")[0]
        wanted = monitor["spec"]["selector"]["matchLabels"]

        services = of_kind(openshift, "Service")
        assert any(
            wanted.items() <= ((s.get("metadata") or {}).get("labels") or {}).items()
            for s in services
        ), f"no Service carries labels {wanted}"
