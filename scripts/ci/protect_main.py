#!/usr/bin/env python3
"""Make the branch rule say what `required-checks.yml` says (SEC-1).

That file opens by claiming to be the source of truth:

    One declaration, in the repository, rather than a branch
    protection rule somebody set in a browser two years ago. The
    rule is generated from this file.

It was not. Nothing read it. The live ruleset on `main` required a
pull request, forbade deletion and forbade force-pushes, and
required **no status checks at all** — so every name in that file,
`Checks` and `Integration (compose)` included, was decorative. A
pull request with a red pipeline could be merged by anyone who
scrolled past the red.

This closes that by generating the ruleset from the file and, with
`--check`, failing when the two disagree. Run it after changing
`required-checks.yml`; `--check` belongs in a job that has a token,
which is why it is not one of the `ci` functions.

    python scripts/ci/protect_main.py --check     # does the rule match?
    python scripts/ci/protect_main.py --apply     # make it match

`--apply` needs `gh` authenticated with `repo` scope on a login
that administers the repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / ".github" / "required-checks.yml"

#: The ruleset's name. Matched on, so renaming it in the browser
#: makes this create a second one rather than edit the first —
#: which is the failure mode, not a reason to avoid naming it.
NAME = "protect-main"


def _repo() -> str:
    """`owner/name` for the repository this checkout points at."""
    out = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def declared_checks() -> list[str]:
    """Every check `required-checks.yml` says must pass, by name.

    The conditional tier is included on purpose. A job skipped by a
    path filter reports success, so requiring it costs nothing when
    it does not run and is the only thing that catches a deployment
    change merging without the cluster tier — which is the case it
    exists for, and is written down as such in that file.
    """
    spoken = yaml.safe_load(DECLARATION.read_text(encoding="utf-8")) or {}

    names: list[str] = []
    for entry in spoken.get("required") or []:
        names.extend(entry.get("checks") or [])
    for entry in spoken.get("conditional") or []:
        if entry.get("check"):
            names.append(entry["check"])
    return sorted(set(names))


def declared_reviews() -> tuple[int, bool]:
    """How many approvals the declaration asks for, and from whom."""
    spoken = yaml.safe_load(DECLARATION.read_text(encoding="utf-8")) or {}
    asked = spoken.get("reviews") or {}
    return int(asked.get("count", 0)), bool(asked.get("code_owners", False))


def wanted(*, signatures: bool) -> dict[str, Any]:
    """The ruleset this repository should have."""
    reviews, owners = declared_reviews()
    rules: list[dict[str, Any]] = [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": reviews,
                "dismiss_stale_reviews_on_push": True,
                "require_code_owner_review": owners,
                "require_last_push_approval": False,
                "required_review_thread_resolution": False,
                "allowed_merge_methods": ["merge", "squash", "rebase"],
            },
        },
        {
            "type": "required_status_checks",
            "parameters": {
                "strict_required_status_checks_policy": False,
                "do_not_enforce_on_create": False,
                "required_status_checks": [
                    {"context": name} for name in declared_checks()
                ],
            },
        },
    ]
    if signatures:
        # Every commit carries a signature GitHub can verify. Not
        # "somebody signed something": the key has to be registered
        # on the account, or the commit reads Unverified and the
        # push is refused.
        rules.append({"type": "required_signatures"})

    return {
        "name": NAME,
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "rules": rules,
        "bypass_actors": [],
    }


TAG_NAME = "protect-tags"


def wanted_tags() -> dict[str, Any] | None:
    """The tag ruleset, or `None` when the declaration asks for none."""
    spoken = yaml.safe_load(DECLARATION.read_text(encoding="utf-8")) or {}
    asked = spoken.get("tags") or {}
    if not asked.get("protected"):
        return None
    return {
        "name": TAG_NAME,
        "target": "tag",
        "enforcement": "active",
        "conditions": {
            "ref_name": {"include": [asked.get("pattern", "**/*")], "exclude": []}
        },
        # Deletion and non-fast-forward only. Creating a tag is what
        # `tag.yml` does on every push to a default branch; moving or
        # removing one after a release was built from it is the thing
        # with no honest reason.
        "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
        "bypass_actors": [],
    }


def live(repo: str, name: str = "") -> dict[str, Any] | None:
    """The ruleset of that name, as the repository has it now."""
    name = name or NAME
    listed = subprocess.run(
        ["gh", "api", f"repos/{repo}/rulesets"],
        capture_output=True,
        text=True,
        check=True,
    )
    for entry in json.loads(listed.stdout or "[]"):
        if entry.get("name") == name:
            one = subprocess.run(
                ["gh", "api", f"repos/{repo}/rulesets/{entry['id']}"],
                capture_output=True,
                text=True,
                check=True,
            )
            found: dict[str, Any] = json.loads(one.stdout)
            return found
    return None


def _comparable(ruleset: dict[str, Any]) -> dict[str, Any]:
    """The parts of a ruleset worth comparing, in a stable order.

    GitHub returns `_links`, `created_at`, ids and a `source`, none
    of which anybody declared. Comparing the whole document reports
    drift on every call.
    """
    rules: dict[str, Any] = {}
    for rule in ruleset.get("rules") or []:
        if rule["type"] == "required_status_checks":
            got = rule.get("parameters", {}).get("required_status_checks", [])
            rules[rule["type"]] = sorted(c["context"] for c in got)
        elif rule["type"] == "pull_request":
            rules[rule["type"]] = rule.get("parameters", {}).get(
                "required_approving_review_count"
            )
        else:
            rules[rule["type"]] = True
    return {
        "enforcement": ruleset.get("enforcement"),
        "rules": rules,
        "bypass": sorted(
            b.get("actor_type", "") for b in (ruleset.get("bypass_actors") or [])
        ),
    }


def differences(have: dict[str, Any] | None, want: dict[str, Any]) -> list[str]:
    """What the live ruleset does not match, in words."""
    if have is None:
        # `want["name"]`, not the module constant. Reporting the
        # branch ruleset as missing while checking the tag one is
        # the kind of wrong answer that sends somebody to the wrong
        # setting.
        return [f"there is no ruleset called {want['name']!r}"]

    here, there = _comparable(have), _comparable(want)
    found: list[str] = []

    if here["enforcement"] != there["enforcement"]:
        found.append(
            f"enforcement is {here['enforcement']!r}, declared {there['enforcement']!r}"
        )
    if here["bypass"]:
        found.append(f"bypass actors are set: {here['bypass']}")

    for kind, expected in there["rules"].items():
        if kind not in here["rules"]:
            found.append(f"the {kind} rule is missing")
        elif here["rules"][kind] != expected:
            found.append(f"{kind} is {here['rules'][kind]!r}, declared {expected!r}")
    return found


def main() -> int:
    """Compare, or apply, the declared ruleset."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check", action="store_true", help="report drift, change nothing"
    )
    group.add_argument(
        "--apply", action="store_true", help="make the rule match the file"
    )
    parser.add_argument(
        "--signatures",
        action="store_true",
        help="also require every commit to carry a verifiable signature",
    )
    chosen = parser.parse_args()

    repo = _repo()

    def put(want: dict[str, Any], have: dict[str, Any] | None) -> int:
        """Create or replace one ruleset. Returns a process code."""
        body = json.dumps(want)
        where = (
            ["-X", "POST", f"repos/{repo}/rulesets"]
            if have is None
            else ["-X", "PUT", f"repos/{repo}/rulesets/{have['id']}"]
        )
        done = subprocess.run(
            ["gh", "api", *where, "--input", "-"],
            input=body,
            capture_output=True,
            text=True,
        )
        if done.returncode != 0:
            print(done.stderr.strip() or done.stdout.strip(), file=sys.stderr)
            return 1
        return 0

    plan: list[tuple[str, dict[str, Any] | None]] = [
        (NAME, wanted(signatures=chosen.signatures)),
        (TAG_NAME, wanted_tags()),
    ]

    worst = 0
    for name, want in plan:
        if want is None:
            continue
        have = live(repo, name)
        drift = differences(have, want)

        if chosen.check:
            print(f"{repo}: {name}")
            if name == NAME:
                for check in declared_checks():
                    print(f"  required: {check}")
            if not drift:
                print("  matches the declaration")
                continue
            print("  does not match `.github/required-checks.yml`:")
            for line in drift:
                print(f"    - {line}")
            worst = 1
            continue

        if not drift:
            print(f"{repo}: {name} already matches the declaration")
            continue
        worst = max(worst, put(want, have))
        if worst == 0:
            print(f"{repo}: {name} applied")
            if name == NAME:
                for check in declared_checks():
                    print(f"  requires {check}")
                if chosen.signatures:
                    print("  requires a verifiable signature on every commit")

    if chosen.check and worst:
        print("\n  python scripts/ci/protect_main.py --apply")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
