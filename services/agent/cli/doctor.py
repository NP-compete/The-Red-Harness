"""What is misconfigured, and what to do about it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    """Ordered worst first, so sorting needs no key function."""

    BLOCKED = 0
    DEGRADED = 1
    NOTE = 2


@dataclass(frozen=True)
class Finding:
    """One thing the doctor found, how bad it is, and what to do."""

    name: str
    severity: Severity
    detail: str
    remedy: str


CHECKS: tuple[tuple[str, Severity, str, str], ...] = (
    (
        "agent_reachable",
        Severity.BLOCKED,
        "The agent did not answer. Everything else here is unknown.",
        "Check the agent is running and that the address this was given points at it.",
    ),
    (
        "config_readable",
        Severity.BLOCKED,
        "The configuration tree could not be read.",
        "Check CONFIG_PATH points at the tree and the process can read it.",
    ),
    (
        "model_key_present",
        Severity.BLOCKED,
        "No model credential is configured, so every run will fail.",
        "Set the provider credential in the environment or the deployment's secret.",
    ),
    (
        "config_clean",
        Severity.DEGRADED,
        "The configuration loaded with problems, so the agent is not "
        "running the configuration that was written.",
        "Run the agent's config check, or look for duplicate-key "
        "warnings from the last load.",
    ),
    (
        "within_limits",
        Severity.DEGRADED,
        "Something is over a limit this deployment set.",
        "Ask the agent which limit, or open the usage page — the "
        "figure and the limit are reported together.",
    ),
    (
        "override_store",
        Severity.DEGRADED,
        "No override store, so changing a capability will be refused "
        "rather than silently lost.",
        "Start the store, or accept that capabilities can only be "
        "changed in configuration.",
    ),
    (
        "versions_agree",
        Severity.DEGRADED,
        "This command is a different build from the agent it is talking to.",
        "Reinstall the client from the same version as the "
        "deployment: one package ships both, and a stale copy "
        "produces errors that read as the agent's.",
    ),
    (
        "tracing_configured",
        Severity.NOTE,
        "No tracing backend, so runs leave no trace to inspect later.",
        "Configure one if you want run history; ignore this if you "
        "deliberately do not.",
    ),
)


def diagnose(world: dict[str, Any]) -> list[Finding]:
    """Everything wrong, worst first."""
    found = [
        Finding(name=name, severity=severity, detail=detail, remedy=remedy)
        for name, severity, detail, remedy in CHECKS
        if name in world and not world[name]
    ]
    return sorted(found, key=lambda f: f.severity)


DEGRADED_EXIT = 5


def exit_code(findings: list[Finding]) -> int:
    """0 usable, 1 unusable, 5 usable but something is missing."""
    if any(f.severity is Severity.BLOCKED for f in findings):
        return 1
    if any(f.severity is Severity.DEGRADED for f in findings):
        return DEGRADED_EXIT
    return 0


def as_json(findings: list[Finding]) -> dict[str, Any]:
    """The same report, for something that is not a person."""
    return {
        "ok": exit_code(findings) == 0,
        "findings": [
            {
                "name": f.name,
                "severity": f.severity.name.lower(),
                "detail": f.detail,
                "remedy": f.remedy,
            }
            for f in findings
        ],
    }
