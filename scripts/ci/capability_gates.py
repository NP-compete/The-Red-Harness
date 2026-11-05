"""A declared flag reaches the capability it names (CFG-1)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "config/agent/runtime/features.yaml"

RESERVED = {
    "planner_enabled": "E14, the planner graph, is not built",
    "swarm_enabled": "E15, multi-agent scale-out, is not built",
    "browser_automation_enabled": "E16, browser automation, is not built",
    "sandbox_backend": "E21, execution backends, is not built",
    "eval_modules_enabled": "E22, eval module breadth, is not built",
    "extraction_ocr_enabled": "E20 shipped without an OCR engine; nothing to gate",
}

UNGATED: dict[str, str] = {}


def declared() -> dict[str, dict]:
    """Every feature declared in the registry."""
    found = (yaml.safe_load(REGISTRY.read_text()) or {}).get("features") or {}
    if not found:
        raise SystemExit(f"{REGISTRY} declares no features")
    return found


def readers(flag: str) -> list[str]:
    """Python files that mention this flag, outside the registry."""
    found = subprocess.run(
        ["grep", "-rl", "--include=*.py", flag, "services/agent"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return [one for one in found.stdout.split() if "__pycache__" not in one]


def problems() -> list[str]:
    """Every declared flag that reaches no code and is not excused."""
    registry = declared()
    found: list[str] = []

    for flag in sorted(registry):
        who = readers(flag)
        excused = flag in RESERVED or flag in UNGATED
        if who and excused:
            found.append(
                f"{flag} is excused as unread and {len(who)} file(s) read it: "
                f"{', '.join(who)}. Remove it from RESERVED/UNGATED — the "
                "capability is gated now."
            )
        elif not who and not excused:
            found.append(
                f"{flag} is declared and nothing reads it. A switch wired to "
                "nothing is offered on the settings page and changes nothing "
                "when it is thrown. Gate the capability, or say why not in "
                "RESERVED or UNGATED."
            )

    for flag in sorted(set(RESERVED) | set(UNGATED)):
        if flag not in registry:
            found.append(f"{flag} is excused here and is not in the registry")

    return found


def main() -> int:
    """Check that every declared capability flag actually gates something."""
    registry = declared()
    found = problems()

    gated = [f for f in sorted(registry) if readers(f)]
    print(f"  {len(gated)} of {len(registry)} declared flag(s) reach code")
    for flag in sorted(RESERVED):
        print(f"    reserved  {flag:<30} {RESERVED[flag]}")
    for flag in sorted(UNGATED):
        print(f"    UNGATED   {flag:<30} built, declared, nothing reads it")

    if not found:
        print("\nevery declared flag either reaches code or says why not")
        return 0
    print("\ncapability gates and the registry disagree:", file=sys.stderr)
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
