"""`python -m agent.src.workflows.entrypoint` — the worker process."""

from __future__ import annotations

import asyncio
import sys


def main() -> int:
    """Run the workflow worker until it is interrupted."""
    from agent.src.workflows.worker import run_worker

    try:
        return asyncio.run(run_worker())
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
