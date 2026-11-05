"""The one image against the two it replaces (E10-T23)."""

from __future__ import annotations

import subprocess
import sys

COMBINED = "harness:local"
PAIR = ("template-agent:local", "template-ui:local")


def size_of(image: str) -> int:
    """Bytes, or 0 when the image is not built here."""
    try:
        found = subprocess.run(
            ["podman", "image", "inspect", image, "--format", "{{.Size}}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception:  # noqa: BLE001
        return 0
    if found.returncode != 0:
        return 0
    try:
        return int(found.stdout.strip())
    except ValueError:
        return 0


def gb(size: int) -> str:
    """`size` rendered in gigabytes."""
    return f"{size / 1_000_000_000:.2f} GB"


def main() -> int:
    """Report the size of the built image."""
    combined = size_of(COMBINED)
    if not combined:
        print(
            f"{COMBINED} is not built. "
            "`podman build -f template-agent/Containerfile -t harness:local .` "
            "from the directory above both checkouts.",
            file=sys.stderr,
        )
        return 2

    parts = {name: size_of(name) for name in PAIR}
    pair = sum(parts.values())

    print(f"{'one image':<24} {gb(combined):>10}  {COMBINED}")
    for name, size in parts.items():
        print(
            f"{'  of the pair':<24} {gb(size):>10}  {name}"
            if size
            else f"{'  of the pair':<24} {'not built':>10}  {name}"
        )
    if not pair:
        print(
            "\nThe two-image baseline is not built here, so there is nothing "
            "to compare with. Build both and run this again.",
            file=sys.stderr,
        )
        return 2

    print(f"{'the pair together':<24} {gb(pair):>10}")
    difference = pair - combined
    if difference >= 0:
        print(f"\nThe one image saves {gb(difference)} against the pair.")
        return 0
    print(
        f"\nThe one image is {gb(-difference)} LARGER than the pair it replaces. "
        "That is the trade strand D says it does not make.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
