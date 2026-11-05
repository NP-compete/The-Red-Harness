"""`make ci` and the pipeline run the same checks (E26-T2, T3)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAKEFILE = REPO / "Makefile"
WORKFLOWS = REPO / ".github" / "workflows"


def _jobs() -> list[str]:
    out = subprocess.run(
        ["make", "--no-print-directory", "ci-jobs"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.split()


def test_the_list_is_not_empty():
    """A target that printed nothing would pass every test below."""
    assert len(_jobs()) >= 4


def test_every_job_names_a_check_or_a_target():
    """A job with nothing behind it fails at the worst moment.

    The names come out of `ci/` now, so most are Dagger functions
    rather than Makefile targets. Both are legitimate; a name that
    is neither is not.
    """
    targets = set(re.findall(r"^([a-z][a-z0-9-]*):", MAKEFILE.read_text(), re.M))
    # A job is legitimate if it is a Makefile target, an entry in
    # CHECKS, or a `@function` in the module — `test` and `ui` are
    # functions rather than CHECKS entries, and listing `ui` without
    # this failed here, which is the test doing its job.
    stray = [
        job
        for job in _jobs()
        if job not in targets
        and job not in set(_dagger_checks())
        and job not in _dagger_functions()
    ]
    assert stray == [], f"`make ci-jobs` names {stray}, which is neither"


def _dagger_checks() -> list[str]:
    """The CHECKS table in the pipeline module."""
    import ast

    tree = ast.parse((REPO / "ci" / "src" / "harness" / "main.py").read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Assign, ast.AnnAssign))
            and "CHECKS" in ast.dump(node)[:200]
        ):
            return sorted(ast.literal_eval(node.value))
    raise AssertionError("no CHECKS table")


def _dagger_functions() -> set[str]:
    """Names decorated with `@function` in the pipeline module."""
    import ast

    tree = ast.parse((REPO / "ci" / "src" / "harness" / "main.py").read_text())
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            getattr(d, "id", getattr(d, "attr", "")) == "function"
            for d in node.decorator_list
        )
    }


def test_the_pipeline_runs_the_same_command_a_developer_runs():
    """Not an equivalent list — the same command.

    This used to check that every job in `make ci-jobs` appeared
    somewhere in a workflow, because there were two lists that had
    to agree. There is one now: the workflow runs `make ci`, which
    runs `dagger call ci`, which is what a laptop runs.
    """
    workflows = " ".join(p.read_text() for p in WORKFLOWS.glob("*.y*ml"))
    assert "run: make ci" in workflows, (
        "no workflow runs `make ci`. The pipeline and a developer "
        "would be running different things again."
    )
    assert "run: make dagger-install" in workflows, (
        "the checks job must install the pinned Dagger CLI, or it "
        "runs whatever the runner happens to have"
    )


def test_the_coverage_floor_has_one_source():
    """The workflow may not hard-code a number the Makefile does not.

    It used to require the literal `coverage-floor`, because the
    workflow ran its own pytest line and interpolated the floor
    into it. It runs `make coverage` now, so the floor never
    leaves the Makefile — a stronger version of the same rule,
    and the assertion had to follow.
    """
    workflows = " ".join(p.read_text() for p in WORKFLOWS.glob("*.y*ml"))
    literal = re.search(r"--cov-fail-under=(\d+)", workflows)
    assert literal is None, (
        f"the floor is hard-coded in a workflow as {literal.group(1)} "
        "again. It belongs in `COVERAGE_FLOOR` so a laptop and the "
        "pipeline cannot disagree."
    )


def test_the_floor_is_not_above_what_the_suite_holds():
    """A gate set above the truth is a gate somebody turns off."""
    floor = int(
        subprocess.run(
            ["make", "--no-print-directory", "coverage-floor"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    assert 0 < floor <= 57, floor
