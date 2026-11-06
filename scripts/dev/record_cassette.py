"""Record what a real model says, once, so tests can replay it (E27-T3)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Both: `agent.*` lives under services/, and anything importing
# `tests.*` needs the repository root as well. An earlier pass
# swapped root for services and broke the scripts that do both.
for _path in (str(REPO_ROOT / "services"), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from tests.fixtures.replay import CASSETTES, record  # noqa: E402

MOCKS = ("mock", "stub")


def main(argv: list[str] | None = None) -> int:
    """Record a cassette of model replies for the given prompts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="the cassette to write")
    parser.add_argument("--prompts", required=True, help="one prompt per line")
    parser.add_argument(
        "--model",
        default=os.environ.get("CASSETTE_MODEL", ""),
        help="the model to record; must not be a mock",
    )
    asked = parser.parse_args(argv)

    model = asked.model.strip()
    if not model:
        print(
            "Name the model to record with --model or CASSETTE_MODEL. This "
            "spends money on purpose, so it will not pick one for you.",
            file=sys.stderr,
        )
        return 2
    if any(mock in model.lower() for mock in MOCKS):
        print(
            f"{model!r} is a mock; recording it would teach nothing.", file=sys.stderr
        )
        return 2

    where = Path(asked.prompts)
    if not where.is_file():
        print(f"no prompts at {where}", file=sys.stderr)
        return 2
    prompts = [line.strip() for line in where.read_text().splitlines() if line.strip()]
    if not prompts:
        print(f"{where} has no prompts in it", file=sys.stderr)
        return 2

    from agent.src.agent.llm import create_model

    llm = create_model(model, temperature=0.0)
    target = CASSETTES / f"{asked.name}.json"

    for prompt in prompts:
        said = llm.invoke([{"role": "user", "content": prompt}])
        content = said.content
        if isinstance(content, list):
            content = " ".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
        reply: dict = {"content": str(content or "")}
        calls = getattr(said, "tool_calls", None)
        if calls:
            first = calls[0]
            import json as _json

            reply["tool_call"] = {
                "id": str(first.get("id") or "call_1"),
                "type": "function",
                "function": {
                    "name": str(first.get("name") or ""),
                    "arguments": _json.dumps(first.get("args") or {}),
                },
            }
        key = record(target, [{"role": "user", "content": prompt}], reply)
        print(f"  {key}  {prompt[:60]}")

    print(f"Recorded {len(prompts)} exchange(s) with {model} into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
