"""The branch rule comes from the file that claims to own it (SEC-1).

`.github/required-checks.yml` says, at the top:

    One declaration, in the repository, rather than a branch
    protection rule somebody set in a browser two years ago. The
    rule is generated from this file.

It was not generated from anything. The live ruleset on `main`
required a pull request, forbade deletion and force-pushes, and
required no status checks whatsoever — so every name in that file
gated nothing, and a pull request with a red pipeline could be
merged by whoever scrolled past the red.

These tests do not reach the network. They check the part that can
be wrong without anybody noticing: that the generator still reads
the declaration, and that what it would send is the shape GitHub
accepts. Whether reality matches is `protect_main.py --check`, run
on a schedule by `ruleset-drift.yml`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci" / "protect_main.py"
DECLARATION = ROOT / ".github" / "required-checks.yml"


def _module():
    """Import the generator without running it."""
    spec = importlib.util.spec_from_file_location("protect_main", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["protect_main"] = module
    spec.loader.exec_module(module)
    return module


def test_the_generator_is_there():
    """Without it every assertion below would hold vacuously."""
    assert SCRIPT.is_file(), f"{SCRIPT} generates the branch rule"


def test_every_declared_check_reaches_the_rule():
    """The names in the file are the names in the payload."""
    spoken = yaml.safe_load(DECLARATION.read_text(encoding="utf-8")) or {}
    expected = {
        name for entry in spoken.get("required") or [] for name in entry["checks"]
    }
    expected |= {
        entry["check"]
        for entry in spoken.get("conditional") or []
        if entry.get("check")
    }

    built = _module().wanted(signatures=False)
    rule = next(r for r in built["rules"] if r["type"] == "required_status_checks")
    got = {c["context"] for c in rule["parameters"]["required_status_checks"]}
    assert got == expected, (
        f"the rule would require {sorted(got)}, the file declares {sorted(expected)}"
    )


def test_an_advisory_check_is_not_required():
    """`License Scan` is declared advisory and must not gate a merge."""
    spoken = yaml.safe_load(DECLARATION.read_text(encoding="utf-8")) or {}
    advisory = {e["check"] for e in spoken.get("advisory") or []}
    assert advisory, "no advisory checks declared, so this proves nothing"

    built = _module().wanted(signatures=False)
    rule = next(r for r in built["rules"] if r["type"] == "required_status_checks")
    got = {c["context"] for c in rule["parameters"]["required_status_checks"]}
    assert not (got & advisory), f"advisory checks are being required: {got & advisory}"


def test_the_rule_forbids_deletion_and_force_pushes():
    kinds = {r["type"] for r in _module().wanted(signatures=False)["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request"} <= kinds


def test_signatures_are_opt_in_and_reach_the_payload():
    """Off by default, because enabling it needs a registered key."""
    module = _module()
    assert "required_signatures" not in {
        r["type"] for r in module.wanted(signatures=False)["rules"]
    }
    assert "required_signatures" in {
        r["type"] for r in module.wanted(signatures=True)["rules"]
    }


def test_tags_are_protected_and_the_pattern_is_one_github_accepts():
    """`**/*` is rejected on a tag ruleset — "Invalid target patterns"."""
    built = _module().wanted_tags()
    assert built is not None, "the declaration no longer protects tags"
    assert built["target"] == "tag"
    patterns = built["conditions"]["ref_name"]["include"]
    assert patterns == ["~ALL"] or all(not p.startswith("**") for p in patterns), (
        f"{patterns} will be refused: a tag ruleset takes `~ALL` or a plain glob"
    )


@pytest.mark.parametrize("key", ["count", "code_owners"])
def test_the_review_requirement_is_declared_not_assumed(key: str):
    spoken = yaml.safe_load(DECLARATION.read_text(encoding="utf-8")) or {}
    assert key in (spoken.get("reviews") or {}), (
        f"reviews.{key} is not declared, so the rule would carry a number "
        "nobody wrote down"
    )
