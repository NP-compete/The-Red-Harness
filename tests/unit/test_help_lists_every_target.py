"""`make help` shows every documented target, under a section.

Help groups by `##@` markers. A target defined above the first
marker, or under a section name that is not in the printed order,
is dropped from the output silently — the target still works, so
nothing fails, and it is simply never discovered.

That is how `make test` and `make install` came to be missing: not
from grouping, but from having no `## ` description at all, which
the flat list hid just as well because nobody reads eighty lines.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"

DOCUMENTED = re.compile(r"^([a-zA-Z_-]+):.*?## ")
SECTION = re.compile(r"^##@ (.+)$")

#: The order `help` prints. A section outside this prints nowhere.
PRINTED = {"Run it", "Test", "Check", "Config and docs", "Measure", "Housekeeping"}

#: Targets a newcomer reaches for first. Undocumented, they are
#: invisible however good the grouping is.
MUST_BE_DOCUMENTED = {"dev", "container", "kind", "test", "ci", "install", "help"}


def _lines() -> list[str]:
    return MAKEFILE.read_text(encoding="utf-8").splitlines()


def _documented() -> set[str]:
    return {m.group(1) for ln in _lines() if (m := DOCUMENTED.match(ln))}


ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _help() -> str:
    """Help output with the colour stripped — it is coloured on a tty."""
    return ANSI.sub("", _raw_help())


def _raw_help() -> str:
    return subprocess.run(
        ["make", "--no-print-directory", "help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout


def test_there_are_targets_to_check():
    """A regex matching nothing would pass everything below."""
    assert len(_documented()) > 20


def test_the_headline_targets_are_documented():
    missing = sorted(MUST_BE_DOCUMENTED - _documented())
    assert not missing, (
        f"{missing} have no `## ` description, so `make help` does not "
        "mention them at all. These are the ones people look for first."
    )


def test_every_section_name_is_one_help_prints():
    used = {m.group(1) for ln in _lines() if (m := SECTION.match(ln))}
    unknown = sorted(used - PRINTED)
    assert not unknown, (
        f"{unknown} are used as `##@` sections and `help` prints only "
        f"{sorted(PRINTED)}. Targets under them vanish from the output."
    )


def test_no_documented_target_sits_above_the_first_section():
    lines = _lines()
    first = next((i for i, ln in enumerate(lines) if SECTION.match(ln)), len(lines))
    stranded = [m.group(1) for ln in lines[:first] if (m := DOCUMENTED.match(ln))]
    assert not stranded, (
        f"{stranded} are documented before the first `##@` marker, so "
        "help has no section to file them under and drops them."
    )


def test_help_prints_every_documented_target():
    shown = set(re.findall(r"^\s+([a-z][a-z0-9_-]*)\s{2,}", _help(), re.M))
    missing = sorted(_documented() - shown)
    assert not missing, f"documented but absent from `make help`: {missing}"
