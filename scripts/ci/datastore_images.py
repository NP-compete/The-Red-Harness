"""One Postgres, one Redis, everywhere (E26-T14)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VALUES = ROOT / "config/agent/deployment/values.yaml"

PLACES = {
    "compose.yaml": ("postgres", "redis"),
    "deployment/components/postgres/deployment.yaml": ("postgres",),
    "deployment/components/redis/deployment.yaml": ("redis",),
    ".github/workflows/test.yml": ("postgres", "redis"),
}

PATTERNS = {
    "postgres": re.compile(r"image:\s*(\S*pgvector\S*)"),
    "redis": re.compile(r"image:\s*(\S*redis\S*)"),
}


def wanted() -> dict[str, str]:
    """The datastore image versions the chart values ask for."""
    values = yaml.safe_load(VALUES.read_text()) or {}
    found = values.get("datastores") or {}
    if not found:
        raise SystemExit(f"{VALUES} has no `datastores:` section")
    return {str(k): str(v) for k, v in found.items()}


def drift() -> list[str]:
    """Every place whose datastore image disagrees with the chart."""
    expected = wanted()
    problems: list[str] = []
    for where, kinds in PLACES.items():
        path = ROOT / where
        if not path.is_file():
            continue
        text = path.read_text()
        for kind in kinds:
            for named in PATTERNS[kind].findall(text):
                if named != expected[kind]:
                    problems.append(
                        f"{where}: {kind} is {named}, values.yaml says {expected[kind]}"
                    )
    return problems


def main() -> int:
    """Check that datastore images agree everywhere they appear."""
    problems = drift()
    if not problems:
        print(
            "datastore images agree: "
            + ", ".join(f"{k} {v}" for k, v in sorted(wanted().items()))
        )
        return 0
    print("datastore images disagree with values.yaml:", file=sys.stderr)
    for one in problems:
        print(f"  {one}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
