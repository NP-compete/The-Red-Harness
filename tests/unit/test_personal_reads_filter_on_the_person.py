"""Every read of a person's rows filters on them in the query (MU-1)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services" / "agent"

PERSONAL = {
    "thread",
    "thread_share",
    "thread_search",
    "user_memories",
    "user_preferences",
    "user_rules",
    "user_consents",
    "message_feedback",
    "projects",
}

IDENTITY = re.compile(
    r"\b(user_id|owner_id|created_by|viewer|identity|username)\b", re.I
)

_FROM = re.compile(r"SELECT\b.*?FROM\s+(\w+)", re.S | re.I)

ALLOWED: dict[str, str] = {
    "services/agent/aegra/thread_cleanup.py": (
        "the `user_id is None` branch of a two-branch lock. The filtered "
        "variant sits directly above it and is what every user-facing "
        "delete takes; the unfiltered one is the deployment acting on its "
        "own data, and it is a visible branch rather than a missing clause"
    ),
    "services/agent/src/analytics/queries.py": (
        "an aggregate over feedback counts. Analytics are deployment-wide "
        "by design and never read message content (PRIV-2), and per-user "
        "disclosure is a separate gated setting (PRIV-3)"
    ),
    "services/agent/src/sharing/store.py": (
        "reading a share by its link id, where the reader is by definition "
        "not the owner. Filtering on the owner here would mean nobody could "
        "ever open a share, which is the whole feature"
    ),
}


def _unfiltered() -> list[tuple[str, int, str]]:
    found: list[tuple[str, int, str]] = []
    for path in sorted(SOURCE.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - not ours to fix
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            statement = node.value
            if "SELECT" not in statement.upper():
                continue
            match = _FROM.search(statement)
            if not match or match.group(1).lower() not in PERSONAL:
                continue
            if IDENTITY.search(statement):
                continue
            found.append(
                (
                    str(path.relative_to(ROOT)),
                    node.lineno,
                    " ".join(statement.split())[:90],
                )
            )
    return found


class TestTheQueryDoesTheFiltering:
    def test_no_unexplained_read(self):
        strays = [
            f"{where}:{line}  {sql}"
            for where, line, sql in _unfiltered()
            if where not in ALLOWED
        ]
        assert not strays, (
            "a read of somebody's rows that does not name them in the "
            "query:\n  " + "\n  ".join(strays)
        )

    def test_the_rule_has_something_to_check(self):
        """Pattern 5: a scan that matches nothing passes."""
        from_personal = 0
        for path in SOURCE.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    match = _FROM.search(node.value)
                    if match and match.group(1).lower() in PERSONAL:
                        from_personal += 1
        assert from_personal >= 20, from_personal


class TestTheExceptionsAreHonest:
    def test_each_is_still_there(self):
        seen = {where for where, _, _ in _unfiltered()}
        gone = sorted(set(ALLOWED) - seen)
        assert not gone, f"{gone} no longer have an unfiltered read — drop them"

    def test_each_says_why(self):
        thin = [k for k, v in ALLOWED.items() if len(v) < 80]
        assert not thin, thin
