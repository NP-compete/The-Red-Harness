"""Build the check registry from the config tree (E22-T1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent.src.evals.registry import Check, CheckRegistry


def _config_text(path: Path) -> str:
    """One answer to what a configuration file says (see `loader`)."""
    from agent.src.agent.config.resolution import effective_text

    return effective_text(path)


CHECKS_DIR = "evals/checks"


def _require(raw: dict[str, Any], key: str, where: str) -> str:
    """The non-empty string at `key`, or raise saying where it was missing."""
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: '{key}' is required and must be a non-empty string")
    return value.strip()


def parse_check(raw: Any, *, source: str) -> Check:
    """One declared check read from its mapping."""
    if not isinstance(raw, dict):
        raise ValueError(f"{source}: expected a mapping")
    return Check(
        name=_require(raw, "name", source),
        group=_require(raw, "group", source),
        decides=_require(raw, "decides", source),
        judge=str(raw.get("judge") or ""),
        dataset=str(raw.get("dataset") or ""),
        cases=tuple(int(c) for c in (raw.get("cases") or ())),
        needs=tuple(str(n) for n in (raw.get("needs") or ())),
        kind=str(raw.get("kind") or "judged"),
        corpus=str(raw.get("corpus") or ""),
        source=source,
    )


def load_checks(root: Path) -> tuple[list[Check], list[dict[str, str]]]:
    """Every declared check, plus the files that would not load."""
    directory = root / CHECKS_DIR
    checks: list[Check] = []
    problems: list[dict[str, str]] = []
    if not directory.is_dir():
        return checks, problems

    seen: dict[str, str] = {}
    for file in sorted(directory.glob("*.yaml")):
        source = f"{CHECKS_DIR}/{file.name}"
        try:
            raw = yaml.safe_load(_config_text(file)) or {}
        except Exception as exc:  # noqa: BLE001 — any parse failure is the answer
            problems.append({"where": source, "what": f"{type(exc).__name__}: {exc}"})
            continue
        try:
            check = parse_check(raw, source=source)
        except ValueError as exc:
            problems.append({"where": source, "what": str(exc)})
            continue
        if check.name in seen:
            problems.append(
                {
                    "where": source,
                    "what": f"duplicate name '{check.name}', also in {seen[check.name]}",
                }
            )
            continue
        seen[check.name] = source
        if check.dataset and not (root / check.dataset).is_file():
            problems.append(
                {"where": source, "what": f"dataset '{check.dataset}' does not exist"}
            )
        checks.append(check)
    return checks, problems


def declared_registry(root: Path) -> tuple[CheckRegistry, list[dict[str, str]]]:
    """The registry of declared checks, and anything wrong with them."""
    checks, problems = load_checks(root)
    return CheckRegistry(checks), problems
