"""Mine the agent's own runs and write the reviews (E12-T5, E12-T7)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)

from agent.cli.observe import ObserveFailed, collect, proposals_for  # noqa: E402
from agent.src.improvement.review import DEFAULT_OUT, write_review  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Read a running agent and write the review document."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=os.environ.get("HARNESS_URL", "http://localhost:5002"),
        help="the agent to read",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="where to write")
    parser.add_argument("--limit", type=int, default=200, help="conversations to read")
    parser.add_argument("--since", default=None, help="ignore anything older")
    parser.add_argument(
        "--ui",
        default=os.environ.get("UI_BASE_URL", "http://localhost:5173"),
        help="base URL for the conversation links in the body",
    )
    parser.add_argument(
        "--print",
        dest="echo",
        action="store_true",
        help=(
            "also print what was written. For a scheduled run, whose only "
            "durable output is its own log"
        ),
    )
    asked = parser.parse_args(argv)

    from datetime import datetime, timezone

    from agent.cli.main import _transport

    os.environ["HARNESS_URL"] = asked.url
    transport = _transport()

    try:
        found = collect(transport=transport, limit=asked.limit, since=asked.since)
    except ObserveFailed as failed:
        print(f"Could not read the agent: {failed}", file=sys.stderr)
        return 1

    try:
        made = proposals_for(found, transport=transport)
    except ObserveFailed as failed:
        print(f"Could not read the configuration: {failed}", file=sys.stderr)
        made = []

    written = write_review(
        made,
        out_dir=asked.out,
        ui_base=asked.ui,
        at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    print(
        f"Read {found.read} conversation(s), {len(found.observations)} observation(s), "
        f"{len(made)} proposal(s)."
    )
    for path in written:
        print(f"  {path}")
    if asked.echo:
        for path in written:
            if path.suffix != ".md":
                continue
            print(f"\n----- {path} -----")
            print(path.read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
