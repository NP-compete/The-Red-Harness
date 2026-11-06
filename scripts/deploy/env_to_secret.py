#!/usr/bin/env python3
"""Filter `.env` down to the keys a cluster should receive."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

INLINE_COMMENT = re.compile(r"\s+#.*$")


def unwrap(value: str) -> str:
    """Strip one layer of matching quotes, as the shell would."""
    value = INLINE_COMMENT.sub("", value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse(env_text: str, keys: set[str]) -> list[tuple[str, str]]:
    """Return the allowlisted, unquoted, non-empty pairs in file order."""
    pairs: list[tuple[str, str]] = []
    for line in env_text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        if key not in keys:
            continue
        value = unwrap(raw)
        if value:
            pairs.append((key, value))
    return pairs


def main() -> int:
    """Turn an env file into a Kubernetes secret, keeping only allowed keys."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=".env", type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--keys", required=True, help="space-separated allowlist")
    args = ap.parse_args()

    if not args.env.is_file():
        print("", file=sys.stderr)
        return 0

    pairs = parse(args.env.read_text(), set(args.keys.split()))

    usable = []
    for key, value in pairs:
        if "\n" in value:
            print(f"skipped {key}: value spans lines", file=sys.stderr)
            continue
        usable.append((key, value))

    args.out.write_text("".join(f"{k}={v}\n" for k, v in usable))
    print(" ".join(k for k, _ in usable), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
