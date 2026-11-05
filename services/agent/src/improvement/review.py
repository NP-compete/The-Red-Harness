"""The thing a person reviews, written down (E12-T5)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DEFAULT_OUT = Path(".local/improvement")

MAX_LINKS = 5


def thread_link(run_id: str, ui_base: str) -> str:
    """Where a person goes to read one of these conversations."""
    base = (ui_base or "").rstrip("/")
    return f"{base}/chat/{run_id}" if base else run_id


def review_body(proposal: Any, *, ui_base: str = "", at: str = "") -> str:
    """One proposal, as a page somebody can act on."""
    lines: list[str] = []
    kind = getattr(proposal, "kind", "") or "observation"
    detail = getattr(proposal, "detail", "") or ""
    lines.append(f"# {kind}: {detail}")
    lines.append("")
    if at:
        lines.append(f"Generated {at} by the improvement loop (E12).")
        lines.append("")

    seen = int(getattr(proposal, "seen", 0) or 0)
    if seen:
        lines.append(f"**Observed** {seen} time(s) in the window read.")
        lines.append("")

    blocked = getattr(proposal, "blocked", "")
    refusal = getattr(proposal, "refusal", "")
    if blocked:
        lines.append("## No change is proposed")
        lines.append("")
        lines.append(blocked)
        lines.append("")
    elif not getattr(proposal, "permitted", True):
        lines.append("## Refused by the control check")
        lines.append("")
        lines.append(refusal or "no reason recorded")
        lines.append("")

    argument = getattr(proposal, "argument", "")
    if argument:
        lines.append("## The argument")
        lines.append("")
        lines.append(argument)
        lines.append("")

    probe = getattr(proposal, "probe", None)
    if probe is not None:
        lines.append("## Against the runs behind it")
        lines.append("")
        lines.append(getattr(probe, "verdict", ""))
        lines.append("")
        lines.append(
            f"- {getattr(probe, 'touched', 0)} call(s) touched, "
            f"{getattr(probe, 'used', 0)} of which fed an answer"
        )
        lines.append(
            "- Read from the recorded conversations. Nothing was re-run: "
            "this deployment resolves configuration once per process, so "
            "a candidate cannot be run beside the live one."
        )
        lines.append("")

    runs = list(getattr(proposal, "runs", []) or [])
    if runs:
        lines.append("## Conversations")
        lines.append("")
        for run in runs[:MAX_LINKS]:
            lines.append(f"- {thread_link(str(run), ui_base)}")
        if len(runs) > MAX_LINKS:
            lines.append(f"- …and {len(runs) - MAX_LINKS} more")
        lines.append("")

    diff = getattr(proposal, "diff", "")
    if diff:
        path = getattr(proposal, "path", "")
        lines.append(f"## The change to `{path}`")
        lines.append("")
        lines.append("```diff")
        lines.append(diff.rstrip("\n"))
        lines.append("```")
        lines.append("")
        lines.append(
            "Apply with `git apply <this file's .patch>` in a checkout, or "
            "paste it into the configuration editor. Nothing here touches a "
            "repository."
        )
        lines.append("")

    return "\n".join(lines)


def _slug(text: str) -> str:
    found = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return found[:50] or "proposal"


def write_review(
    proposals: list[Any],
    *,
    out_dir: Path | str = DEFAULT_OUT,
    ui_base: str = "",
    at: str = "",
) -> list[Path]:
    """Write one body per proposal, a patch for each real change, and an index."""
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    rows: list[str] = []
    for number, proposal in enumerate(proposals, start=1):
        stem = f"{number:02d}-{_slug(getattr(proposal, 'kind', ''))}"
        body = root / f"{stem}.md"
        body.write_text(review_body(proposal, ui_base=ui_base, at=at))
        written.append(body)

        diff = getattr(proposal, "diff", "")
        if diff:
            patch = root / f"{stem}.patch"
            patch.write_text(diff if diff.endswith("\n") else diff + "\n")
            written.append(patch)

        rows.append(f"- [{stem}]({body.name}) — {_disposition(proposal)}")

    index = root / "index.md"
    index.write_text(
        "\n".join(
            [
                "# What the improvement loop proposed",
                "",
                (at and f"Generated {at}.") or "",
                "",
                *(rows or ["Nothing in the window read implies a change."]),
                "",
            ]
        )
    )
    return [index, *written]


def _disposition(proposal: Any) -> str:
    if getattr(proposal, "blocked", ""):
        return "no change proposed"
    if not getattr(proposal, "permitted", True):
        return "refused by the control check"
    probe = getattr(proposal, "probe", None)
    if probe is not None and getattr(probe, "used", False):
        return "proposed — but the probe argues against it"
    return "proposed"
