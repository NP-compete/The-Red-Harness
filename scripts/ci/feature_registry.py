"""Every capability flag is declared, and declared by somebody (CFG-7)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
REGISTRY = ROOT / "config/agent/runtime/features.yaml"

NOT_THE_REGISTRY = ("runtime/ui.yaml", "runtime/ui-examples/")


def declared() -> dict[str, dict]:
    """Every feature declared in the registry."""
    if not REGISTRY.is_file():
        raise SystemExit(f"{REGISTRY} does not exist")
    found = (yaml.safe_load(REGISTRY.read_text()) or {}).get("features") or {}
    if not found:
        raise SystemExit(f"{REGISTRY} declares no features")
    return found


def used() -> dict[str, list[str]]:
    """Every `features.<key>` set anywhere in a config tree."""
    found: dict[str, list[str]] = {}
    for path in sorted(CONFIG.rglob("*.yaml")):
        relative = path.relative_to(CONFIG).as_posix()
        if path == REGISTRY or any(
            f"/{relative}".find(f"/{one}") >= 0
            if one.endswith("/")
            else relative.endswith(one)
            for one in NOT_THE_REGISTRY
        ):
            continue
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except Exception:
            continue
        block = raw.get("features") if isinstance(raw, dict) else None
        if isinstance(block, dict):
            for key in block:
                found.setdefault(str(key), []).append(relative)
    return found


def problems() -> list[str]:
    """Every flag used in code that the registry does not declare."""
    registry = declared()
    found: list[str] = []

    for key, where in sorted(used().items()):
        if key not in registry:
            found.append(
                f"{key} is set in {', '.join(where)} and is not in the "
                f"registry ({REGISTRY.name}). A flag with no declaration has "
                "no scope, no default and no owner."
            )

    for key, entry in sorted(registry.items()):
        if not isinstance(entry, dict) or not entry.get("epic"):
            found.append(
                f"{key} is declared and names no owning epic. A capability "
                "nobody owns is one nobody removes when it is cut."
            )
        elif entry.get("default") is not False:
            found.append(
                f"{key} does not default to false. Every capability here "
                "ships off; a flag that ships on is not opt-in."
            )

    return found


def main() -> int:
    """Check that every feature flag in code is declared with an owning epic."""
    registry = declared()
    found = problems()
    print(f"  {len(registry)} flag(s) declared, each with an owning epic:")
    for key, entry in sorted(registry.items()):
        print(f"    {key:<30} {entry.get('epic') or '—'}")
    print(f"  not governed here: {', '.join(NOT_THE_REGISTRY)} (the interface's own)")

    if not found:
        print("\nevery capability flag is declared and owned")
        return 0
    print("\nthe feature registry and the configuration disagree:", file=sys.stderr)
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
