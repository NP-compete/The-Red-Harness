"""Validate an agent's `config/` directory."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from agent._root import CONFIG_ROOT
from agent.src.settings import settings


def _text(path: Path) -> str:
    """A config file as the agent would read it, overlay included."""
    from agent.src.agent.config.resolution import effective_text

    return effective_text(path)


@dataclass
class Finding:
    """One problem, located precisely enough to fix without searching."""

    file: str
    location: str
    message: str
    level: str = "error"

    def render(self) -> str:
        """One finding as an aligned line for the terminal."""
        where = f"{self.file}:{self.location}" if self.location else self.file
        return f"  {self.level.upper():7} {where}\n          {self.message}"


@dataclass
class Report:
    """Everything config validation found, errors and warnings together."""

    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        """Findings that should stop a deployment."""
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        """Findings worth reading that should not stop a deployment."""
        return [f for f in self.findings if f.level == "warning"]

    def add(self, file: str, location: str, message: str, level: str = "error") -> None:
        """Record a finding against a file and a location inside it."""
        self.findings.append(Finding(file, location, message, level))


def _pydantic_location(error: Mapping[str, Any]) -> str:
    """Render a pydantic error path as a config path a human can grep."""
    parts = [str(p) for p in error.get("loc", ())]
    return ".".join(parts) if parts else "(root)"


def _validate_each(
    report: Report, path: Path, rel: str, model: type[BaseModel], section: str
) -> None:
    """Validate every entry of a section keyed by name."""
    if not path.is_file():
        return

    try:
        raw = yaml.safe_load(_text(path)) or {}
    except yaml.YAMLError:
        return

    entries = raw.get(section) or {}
    if not isinstance(entries, dict):
        report.add(rel, section, f"'{section}' should be a mapping of named entries")
        return

    from agent.src.agent.config.unknown_keys import unknown_keys

    for name, value in entries.items():
        where = f"{section}.{name}"
        if not isinstance(value, dict):
            continue
        for problem in unknown_keys(value, model, where):
            report.add(rel, where, problem)
        try:
            model(**value)
        except ValidationError as exc:
            for error in exc.errors():
                report.add(rel, f"{where}.{_pydantic_location(error)}", error["msg"])
        except Exception as exc:
            report.add(rel, where, str(exc))


def _validate_model(
    report: Report, path: Path, rel: str, model: type[BaseModel], section: str | None
) -> BaseModel | None:
    """Parse one YAML file into a model, reporting field-level errors."""
    if not path.is_file():
        return None

    try:
        raw = yaml.safe_load(_text(path)) or {}
    except yaml.YAMLError as exc:
        report.add(rel, "", f"Not valid YAML: {exc}")
        return None

    if section is not None:
        raw = raw.get(section) or {}

    from agent.src.agent.config.unknown_keys import unknown_keys

    for problem in unknown_keys(raw, model, section or ""):
        report.add(rel, "", problem)

    try:
        return model(**raw)
    except ValidationError as exc:
        for error in exc.errors():
            report.add(rel, _pydantic_location(error), error["msg"])
    except Exception as exc:
        report.add(rel, "", str(exc))
    return None


_MARKERS_FILE = settings.TEMPLATE_MARKERS_FILE


def _example_markers(config_dir: Path) -> list[tuple[str, str, str]]:
    """Load the marker list. A missing or unreadable file means none."""
    path = config_dir / _MARKERS_FILE
    if not path.is_file():
        return []
    try:
        raw = yaml.safe_load(_text(path)) or {}
        entries = raw.get("markers") or []
    except Exception:
        return []

    markers: list[tuple[str, str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        needle = str(entry.get("needle") or "")
        rel = str(entry.get("file") or "")
        if needle and rel:
            markers.append(
                (needle, rel, str(entry.get("message") or "is still the example's"))
            )
    return markers


def _check_example_leftovers(report: Report, config_dir: Path) -> None:
    """Warn about demo content a fork should have replaced."""
    for needle, rel, message in _example_markers(config_dir):
        path = config_dir / rel
        if not path.is_file():
            continue
        if needle in _text(path):
            report.add(rel, "", f"{message} ({needle!r})", level="warning")


def _check_placeholder_secrets(report: Report, config_dir: Path) -> None:
    """Catch unreplaced placeholders that would fail only at first use."""
    mcp = config_dir / "integrations" / "mcp.json"
    if not mcp.is_file():
        mcp = config_dir / "mcp.json"
    if not mcp.is_file():
        return

    text = _text(mcp)
    if 'ssl_verify": false' in text or '"ssl_verify": false' in text:
        report.add(
            "mcp.json",
            "ssl_verify",
            "TLS verification disabled; forced on in production but unsafe elsewhere",
            level="warning",
        )


def validate_config(config_dir: Path) -> Report:
    """Validate every config file we have a model for."""
    from agent.src.agent.config.cache import CacheFileConfig
    from agent.src.agent.config.filesystem import FilesystemFileConfig
    from agent.src.agent.config.middleware import (
        ExecutionConfig,
        MiddlewareDefaults,
        PIIConfig,
    )
    from agent.src.agent.config.opa import OpaFileConfig
    from agent.src.agent.config.otel import OtelFileConfig
    from agent.src.agent.config.providers import (
        AsyncTaskConfig,
        HarnessProfileConfig,
        ProviderConfig,
    )
    from agent.src.attachments.config import (
        AttachmentsConfig,
        ExtractionConfig,
    )
    from agent.src.channels.config import ChannelsFileConfig
    from agent.src.routing.config import RouterConfig

    report = Report()

    if not config_dir.is_dir():
        report.add(str(config_dir), "", "Config directory does not exist")
        return report

    targets: list[tuple[str, type[BaseModel], str | None]] = [
        ("runtime/agent.yaml", MiddlewareDefaults, "middleware"),
        ("runtime/agent.yaml", CacheFileConfig, "cache"),
        ("runtime/agent.yaml", FilesystemFileConfig, "filesystem"),
        ("runtime/agent.yaml", OpaFileConfig, "opa"),
        ("runtime/agent.yaml", ExecutionConfig, "execution"),
        ("runtime/agent.yaml", AsyncTaskConfig, "async_tasks"),
        ("runtime/observability.yaml", OtelFileConfig, "otel"),
        ("runtime/agent.yaml", AttachmentsConfig, "attachments"),
        ("runtime/agent.yaml", ExtractionConfig, "extraction"),
        ("runtime/pii.yaml", PIIConfig, None),
        ("runtime/router.yaml", RouterConfig, None),
        ("integrations/channels.yaml", ChannelsFileConfig, None),
    ]

    for rel, model, section in targets:
        _validate_model(report, config_dir / rel, rel, model, section)

    each: list[tuple[str, type[BaseModel], str]] = [
        ("runtime/agent.yaml", ProviderConfig, "providers"),
        ("runtime/agent.yaml", HarnessProfileConfig, "harness_profiles"),
    ]
    for rel, model, section in each:
        _validate_each(report, config_dir / rel, rel, model, section)

    _check_required_files(report, config_dir)
    _check_agent_sections(report, config_dir)
    _check_readers_that_refuse(report, config_dir)

    _check_duplicate_keys(report, config_dir)
    _check_example_leftovers(report, config_dir)
    _check_placeholder_secrets(report, config_dir)
    _check_legacy_paths(report, config_dir)
    _check_schema_version(report, config_dir)
    return report


def _check_schema_version(report: Report, config_dir: Path) -> None:
    """Report a tree this build would refuse to start on."""
    from agent.src.agent.config.schema_version import (
        TooNew,
        TooOld,
        check_schema_version,
    )

    for rel in ("runtime/agent.yaml", "agent.yaml"):
        path = config_dir / rel
        if not path.is_file():
            continue
        try:
            raw = yaml.safe_load(_text(path)) or {}
        except (OSError, yaml.YAMLError):
            return

        declared = raw.get("schema_version") if isinstance(raw, dict) else None
        if declared is not None and not isinstance(declared, int):
            report.add(
                rel, "schema_version", f"must be a whole number, not {declared!r}"
            )
            return

        found = check_schema_version(declared)
        if isinstance(found, (TooOld, TooNew)):
            report.add(rel, "schema_version", found.message)
        return


def _check_duplicate_keys(report: Report, config_dir: Path) -> None:
    """Catch a setting written twice, which YAML discards in silence."""
    from agent.src.agent.config.duplicate_keys import duplicate_keys

    for path in sorted(config_dir.rglob("*.yaml")) + sorted(config_dir.rglob("*.yml")):
        try:
            text = _text(path)
        except OSError:
            continue
        for problem in duplicate_keys(text):
            report.add(str(path.relative_to(config_dir)), "", problem)


AGENT_SECTIONS: dict[str, str] = {
    "analytics": "",
    "bench": "",
    "async_tasks": "",
    "attachments": "",
    "cache": "",
    "execution": "",
    "extraction": "",
    "filesystem": "",
    "guardrail": "",
    "harness_profiles": "",
    "knowledge": "",
    "limits": "",
    "middleware": "",
    "model": "",
    "name": "",
    "opa": "",
    "providers": "",
    "resolve_strategy": "",
    "schema_version": "",
    "token_budget": "",
    "logging": "nothing reads it; the level comes from PYTHON_LOG_LEVEL",
    "memory": (
        "nothing reads it — the consolidation, decay, clustering and "
        "scheduler settings here come from MEMORY_* environment variables"
    ),
    "platform": (
        "nothing reads it; platform.audit comes from "
        "PLATFORM_AUDIT_ENABLED and PLATFORM_AUDIT_BUFFER_MAX"
    ),
    "server": "nothing reads it; the port comes from AGENT_PORT",
}


def _check_agent_sections(report: Report, config_dir: Path) -> None:
    """Every top-level key in `agent.yaml` is one this build reads."""
    import yaml

    path = config_dir / "runtime" / "agent.yaml"
    if not path.is_file():
        return
    try:
        raw = yaml.safe_load(_text(path)) or {}
    except Exception:
        return
    if not isinstance(raw, dict):
        return

    for key in sorted(raw):
        if key not in AGENT_SECTIONS:
            report.add(
                "runtime/agent.yaml",
                key,
                f"unknown top-level section {key!r} — this build reads none "
                "of it, so anything set under it does nothing",
            )


def _check_readers_that_refuse(report: Report, config_dir: Path) -> None:
    """Run the readers that already refuse bad configuration."""
    import yaml

    from agent.src.agent.config.inbound import read_inbound
    from agent.src.knowledge.config import read_knowledge

    for rel, reader, section in (
        ("runtime/agent.yaml", read_knowledge, "knowledge"),
        ("integrations/mcp_server.yaml", read_inbound, "mcp_server"),
    ):
        path = config_dir / rel
        if not path.is_file():
            continue
        try:
            raw = yaml.safe_load(_text(path)) or {}
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        try:
            reader(raw)
        except ValueError as refused:
            report.add(rel, section, str(refused))


def _check_required_files(report: Report, config_dir: Path) -> None:
    """Assert the files the agent cannot start without are present."""
    from agent.src.agent.config.paths import _CANDIDATES, config_root

    required = ("prompt", "mcp", "agent")
    use_resolver = config_dir == config_root()

    for name in required:
        candidates = _CANDIDATES[name]
        if use_resolver:
            from agent.src.agent.config.paths import config_file

            found = config_file(name) is not None
        else:
            found = any((config_dir / rel).is_file() for rel in candidates)

        if not found:
            report.add(
                candidates[0],
                "",
                f"Required config '{name}' is missing "
                f"(looked for: {', '.join(candidates)})",
            )


def _check_legacy_paths(report: Report, config_dir: Path) -> None:
    """Report config files still at a pre-rename path."""
    from agent.src.agent.config.paths import config_root, describe_layout

    if config_dir != config_root():
        return

    for name, info in sorted(describe_layout().items()):
        if info["legacy"]:
            report.add(
                str(info["path"]),
                "",
                f"legacy path for '{name}' — rename to {info['preferred']!r}",
                level="warning",
            )


def main() -> int:
    """Print the report. Non-zero exit on any error."""
    config_dir = Path(
        os.getenv(
            "CONFIG_PATH",
            str(CONFIG_ROOT),
        )
    )

    report = validate_config(config_dir)

    print(f"Validating {config_dir}\n")
    for finding in report.findings:
        print(finding.render())

    if not report.findings:
        print("  OK — no problems found")

    print(f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
