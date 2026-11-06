"""Every pipeline step is a Makefile target (CI-1)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

DOING_WORK = {"test.yml", "pre-commit.yml"}

_IS_MAKE = re.compile(r"(sudo\s+)?make\b")

PIPELINE_MECHANICS: dict[str, str] = {
    "Test summary": (
        "writes to $GITHUB_STEP_SUMMARY, which does not exist off CI and "
        "produces no artefact a developer could want locally"
    ),
    "Install kind": (
        "installs the tool the next steps use. A developer running Kind "
        "already has it; installing it is the runner's setup, not the work"
    ),
    "Install Gitleaks": (
        "the same: fetching a binary the runner lacks and a developer has "
        "through their own package manager"
    ),
    "What the cluster was doing": (
        "a diagnostic dump that only runs on failure, to put the cluster's "
        "state in the log where the failure is read"
    ),
}

NOT_YET_A_TARGET: dict[str, str] = {
    "Check new code coverage": "`make coverage-floor`",
    "Start the agent": "a target; the compose and kind paths have one already",
    "Create the cluster": "`make kind`",
    "Build and load the image": "part of `make kind`",
    "Deploy": "part of `make kind`",
    "Gitleaks full history scan": "a `make secrets-scan` target",
}


def non_make_steps() -> list[tuple[str, str, str]]:
    """Steps in the work workflows that run something other than make."""
    found: list[tuple[str, str, str]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        if path.name not in DOING_WORK:
            continue
        document = yaml.safe_load(path.read_text()) or {}
        for job in (document.get("jobs") or {}).values():
            for step in job.get("steps") or []:
                script = step.get("run")
                if not script:
                    continue
                lines = [
                    line.strip()
                    for line in script.splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
                stray = [line for line in lines if not _IS_MAKE.match(line)]
                if stray:
                    found.append(
                        (path.name, step.get("name", "(unnamed)"), stray[0][:70])
                    )
    return found


def main() -> int:
    """Check that every workflow step doing real work calls `make`."""
    found = non_make_steps()
    known = set(PIPELINE_MECHANICS) | set(NOT_YET_A_TARGET)
    strays = [(w, n, c) for w, n, c in found if n not in known]

    if not strays:
        print(f"  every step in {', '.join(sorted(DOING_WORK))} is `make …`")
        print(f"  or one of {len(PIPELINE_MECHANICS)} named pipeline mechanics")
        print(f"  {len(NOT_YET_A_TARGET)} still to become targets — may only shrink")
        print("\nno new step exists only in CI")
        return 0

    print("workflow steps that exist only in CI:", file=sys.stderr)
    for where, name, command in strays:
        print(f"  {where}  {name}\n      {command}", file=sys.stderr)
    print(
        "\nCI-1: a step that is not a Makefile target cannot be run locally, so "
        "`make ci` can pass while the pipeline fails. Give it a target, or add "
        "it to PIPELINE_MECHANICS with a reason if it genuinely cannot be one.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
