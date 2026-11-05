"""Every check in the pipeline runs something that exists (CI-7).

Replaces `test_a_ci_job_without_a_rule_fails.py`. That guarded the
Makefile's `make ci JOB=<name>` dispatch, where a job listed with
no rule behind it hit the catch-all and reported green having run
nothing. The dispatch is gone — the pipeline is `ci/` now — but the
hazard is the same shape: a name in `CHECKS` whose script does not
exist.

It is a cheaper failure than it used to be, because the container
exits non-zero on a missing file rather than passing. It is still
worth catching here: a full container build to learn that a script
is called `tautological_asserts.py` and not `tautologies.py` costs
forty seconds, and this costs none.
"""

from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "ci" / "src" / "harness" / "main.py"


def _checks() -> dict[str, list[str]]:
    """The CHECKS table, read without importing the dagger SDK."""
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and getattr(node.target, "id", "") == "CHECKS"
        ):
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "CHECKS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"no CHECKS table in {MODULE}")


def test_the_module_is_there():
    """Without it every assertion below would vacuously hold."""
    assert MODULE.is_file(), f"{MODULE} is the pipeline"


def test_there_are_checks():
    assert len(_checks()) > 5


def test_every_check_runs_python():
    odd = {name: argv for name, argv in _checks().items() if argv[0] != "python"}
    assert not odd, (
        f"these do not start with `python`, so the container may not have them: {odd}"
    )


def test_every_script_exists():
    missing = {}
    for name, argv in _checks().items():
        if "-m" in argv:
            continue
        script = next((a for a in argv[1:] if a.endswith(".py")), None)
        if script and not (ROOT / script).is_file():
            missing[name] = script
    assert not missing, (
        f"these name a script that is not in the tree: {missing}. "
        "The check would fail in the container with `can't open file`."
    )


def test_every_module_is_importable():
    missing = {}
    for name, argv in _checks().items():
        if "-m" not in argv:
            continue
        dotted = argv[argv.index("-m") + 1]
        path = ROOT / "services" / (dotted.replace(".", "/") + ".py")
        alt = ROOT / (dotted.replace(".", "/") + ".py")
        pkg = ROOT / "services" / dotted.replace(".", "/")
        if not (path.is_file() or alt.is_file() or pkg.is_dir()):
            missing[name] = dotted
    assert not missing, f"`python -m` names that resolve to nothing: {missing}"
