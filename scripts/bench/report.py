"""Reading two configurations against each other."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)

from scripts.bench.results import compare, read_rows, unmatched  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Compare two recorded benchmark runs."""
    parser = argparse.ArgumentParser(prog="bench-compare")
    parser.add_argument("--results", default="data/bench/results.jsonl")
    parser.add_argument(
        "--compare", nargs=2, metavar=("BEFORE", "AFTER"), required=True
    )
    args = parser.parse_args(argv)

    rows = read_rows(Path(args.results))
    before, after = args.compare

    try:
        found = compare(rows, before, after)
    except ValueError as refused:
        print(f"Cannot compare: {refused}", file=sys.stderr)
        return 2

    print(f"{before} -> {after}\n")
    for delta in found:
        print(
            f"  {delta.suite:<8} {delta.before:>6.3f} -> {delta.after:>6.3f}   {delta.delta:+.3f}"
        )

    missing = unmatched(rows, before, after)
    if missing:
        print(f"\n  not compared (only one side ran): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
