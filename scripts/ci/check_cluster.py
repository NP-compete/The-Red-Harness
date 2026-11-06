"""The checks only a cluster can make (E26-T15)."""

from __future__ import annotations

import json
import subprocess
from typing import Any

NAMESPACE = "template-agent"
ROLES = ("agent", "ui")


def kubectl(*args: str) -> tuple[int, str]:
    """Run kubectl in the namespace and return the code and output."""
    found = subprocess.run(
        ["kubectl", "-n", NAMESPACE, *args], capture_output=True, text=True, timeout=120
    )
    return found.returncode, found.stdout.strip() or found.stderr.strip()


def deployments() -> dict[str, Any]:
    """Every deployment in the namespace, keyed by name."""
    code, out = kubectl("get", "deploy", "-o", "json")
    if code != 0:
        raise SystemExit(f"Could not read the deployments: {out}")
    return {one["metadata"]["name"]: one for one in json.loads(out)["items"]}


def check(name: str, ok: bool, detail: str, how: str) -> bool:
    """Print one check result, with how to fix it if it failed."""
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        print(f"        {how}")
    return ok


def main() -> int:
    """Check every expected deployment in the cluster."""
    found = deployments()
    passed = True

    for role in ROLES:
        one = found.get(role)
        if one is None:
            passed = check(
                role, False, "no such deployment", f"kubectl -n {NAMESPACE} get deploy"
            )
            continue
        spec = one["spec"]["template"]["spec"]
        container = spec["containers"][0]
        ready = one.get("status", {}).get("readyReplicas") or 0

        passed &= check(
            f"{role} ready",
            ready >= 1,
            f"{ready} replica(s) ready",
            f"kubectl -n {NAMESPACE} describe deploy {role}",
        )
        passed &= check(
            f"{role} probes",
            bool(container.get("readinessProbe")),
            "declares a readiness probe"
            if container.get("readinessProbe")
            else "no readiness probe, so a broken pod takes traffic",
            f"kubectl -n {NAMESPACE} get deploy {role} -o yaml | grep -A5 readinessProbe",
        )
        links = spec.get("enableServiceLinks")
        passed &= check(
            f"{role} service links",
            links is False,
            "off" if links is False else f"on ({links!r})",
            "Kubernetes injects AGENT_PORT=tcp://… for every service in the "
            "namespace and pydantic refuses it; set serviceLinks.enabled: false",
        )

    images = {
        role: found[role]["spec"]["template"]["spec"]["containers"][0]["image"]
        for role in ROLES
        if role in found
    }
    passed &= check(
        "one image",
        len(set(images.values())) == 1,
        " and ".join(sorted(set(images.values()))),
        "E10 strand D: both roles run one image and tag, with the role in args",
    )

    for role, path in (("agent", "/health"), ("ui", "/api/health")):
        code, out = kubectl(
            "exec",
            f"deploy/{role}",
            "--",
            "python" if role == "agent" else "node",
            "-c" if role == "agent" else "-e",
            (
                "import urllib.request;"
                "print(urllib.request.urlopen('http://127.0.0.1:5002/health').status)"
            )
            if role == "agent"
            else "fetch('http://127.0.0.1:8080/api/health').then(r=>console.log(r.status))",
        )
        passed &= check(
            f"{role} answers {path}",
            code == 0 and "200" in out,
            out.splitlines()[-1] if out else "no answer",
            f"kubectl -n {NAMESPACE} logs deploy/{role} --tail=20",
        )

    print("\ncluster checks passed" if passed else "\ncluster checks FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
