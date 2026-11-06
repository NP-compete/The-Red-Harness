"""No directory of tests that nothing runs.

`tests/contracts` and `tests/integration` held 99 tests between
them and appeared in no CI job. Two of the contract tests were
failing and nine of the integration ones could never have passed
— they pointed at a port nothing in this repository listens on.
Nobody knew, because a suite that is never invoked reports
nothing at all; it does not report zero.

Both folders are gone now: their tests sit beside the code they
exercise and carry the `integration` marker explicitly, instead
of being stamped by whichever directory they happened to be in.
A marker and a folder saying the same thing is one of them too
many, and the folder is the half that gets forgotten.

So: every directory under `tests/` holding `test_*.py` is either
inside what `make test` collects, or named in `make ci-skipped`
with a reason. Adding a suite and forgetting to wire it up fails
here, which is the only moment the omission is cheap.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Deselected by `make test` on purpose. Each costs something the
#: per-PR run should not pay: live model calls, or a running stack.
#: Markers, not folders — `tests/skills/` and `tests/nightly/` held
#: one file each and existed only to say what the marker already said.
DESELECTED = ("skills", "nightly")

#: `tests/` holds these and nothing else: the suite, what it reads,
#: and the k6 load tests, which are a different runner entirely.
FOLDERS = {"unit", "fixtures", "load"}


def _make_test_recipe() -> str:
    """The pytest line `make test` actually runs."""
    lines = (ROOT / "Makefile").read_text().splitlines()
    # `test:` carries a `## ` description now, so an exact match
    # finds nothing.
    start = next(i for i, ln in enumerate(lines) if ln.startswith("test:"))
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(("\t", " ")):
            break
        body.append(line)
    found = [one for one in body if "pytest" in one]
    assert found, "no pytest invocation in the `test:` target"
    return "\n".join(found)


def _test_files() -> list[pathlib.Path]:
    return [
        path
        for path in (ROOT / "tests").rglob("test_*.py")
        if "__pycache__" not in path.parts
    ]


def _suites() -> set[str]:
    found = {
        str(path.parent.relative_to(ROOT))
        for path in (ROOT / "tests").rglob("test_*.py")
        if "__pycache__" not in path.parts
    }
    # Report the top two levels, which is the granularity a job runs.
    return {"/".join(one.split("/")[:2]) for one in found}


def test_there_are_suites_to_check():
    """A glob that matched nothing would pass everything below."""
    assert _suites()


def test_make_test_runs_the_whole_tree_not_one_subdirectory():
    """The guard that can actually regress.

    `pytest tests` picks up a new directory on its own, so an
    orphan suite cannot appear while the recipe says `tests`. It
    reappears the moment somebody narrows that to `tests/unit` —
    which is what it said before, and how 99 tests went unrun. So
    check the recipe, not the collection.
    """
    recipe = _make_test_recipe()
    assert "pytest tests" in recipe, (
        f"`make test` runs `{recipe.strip()}`. It must collect all of "
        "tests/, or suites added later run nowhere."
    )
    narrowed = [
        one
        for one in sorted(_suites())
        if f"pytest {one}" in recipe or f"--ignore={one}" in recipe
    ]
    assert not narrowed, f"`make test` singles out {narrowed}; it should take tests/"


def test_tests_holds_only_the_folders_it_is_supposed_to():
    """Thirteen directories once, for three kinds of thing."""
    found = {
        one.name
        for one in (ROOT / "tests").iterdir()
        if one.is_dir() and not one.name.startswith((".", "__"))
    }
    assert found == FOLDERS, (
        f"tests/ holds {sorted(found)}; it should hold {sorted(FOLDERS)}. "
        "Tests go in unit/ with a marker, data and helpers in fixtures/."
    )


def test_what_is_deselected_is_named_in_ci_skipped():
    said = subprocess.run(
        ["make", "--no-print-directory", "ci-skipped"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    for marker in DESELECTED:
        assert marker in said, (
            f"'{marker}' is deselected from `make test` and "
            "`make ci-skipped` does not mention it"
        )


def test_the_deselected_markers_actually_select_something():
    """A marker that matches nothing deselects nothing.

    This read the test sources for `mark.skills` and was happy.
    Meanwhile `pytest -m skills` collected **zero**: the suite is
    parametrised by a `pytest_generate_tests` hook whose root path
    was counted in `.parent`s, and moving the file one level deeper
    made it skip. Grep saw the marker; pytest saw no tests. Only
    collection can tell you the difference.
    """
    for marker in DESELECTED:
        found = subprocess.run(
            [
                # `sys.executable`, not the venv path: the CI
                # container installs system-wide and has no .venv,
                # so a hard-coded path made this the only test that
                # could not run where the pipeline runs.
                sys.executable,
                "-m",
                "pytest",
                "tests",
                "-m",
                marker,
                "--collect-only",
                "-q",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        count = sum(1 for line in found.splitlines() if "::" in line)
        assert count, (
            f"`pytest -m {marker}` collects nothing, so deselecting it "
            "from `make test` does nothing and the suite it is meant to "
            "hold back is not running anywhere either"
        )
