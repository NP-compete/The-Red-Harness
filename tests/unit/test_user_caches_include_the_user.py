"""A cache keyed on anything user-specific includes the user (MU-3)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services" / "agent"

CACHES: dict[str, str] = {
    "_graph_cache": (
        "`_graph_fingerprint(..., user_identity=...)` — the compiled graph "
        "differs per person because their tools and approvals do"
    ),
    "_graph_cache_ts": (
        "the same key as `_graph_cache`, holding its age; a satellite of "
        "that cache rather than a cache of its own"
    ),
    "_cached_tools": (
        'keyed `f"{user_id}:{server_key}"` — one person\'s connected servers '
        "are not another's"
    ),
    "_cached_tools_ts": (
        "the same key as `_cached_tools`, holding its age; a satellite of "
        "that cache rather than a cache of its own"
    ),
    "_cached_connected_set": (
        "the same key as `_cached_tools`, holding which servers that person "
        "had connected when the list was built"
    ),
    "_user_token_cache": (
        "keyed on the user id and holding their tokens; bounded at 512 with "
        "least-recently-used eviction (SCALE-3)"
    ),
    "_memory_cache": (
        'LDAP membership, keyed `f"ldap:membership:{user_id}:{group_cn}"` — a '
        "shared key here would be one person's roles answering for another's"
    ),
    "_METADATA_CACHE": (
        "NO USER, deliberately: an MCP server's published OAuth metadata, "
        "identical for every caller. Keying it per person would multiply it "
        "by the user count and cache nothing new"
    ),
    "_ICON_CACHE": (
        "NO USER, deliberately: a server's icon image, the same bytes for everyone"
    ),
}

_CACHEY = re.compile(r"cache|_cached|sessions|_store$", re.I)


def _module_level_caches() -> set[str]:
    """Every module-level dict that looks like a cache."""
    found: set[str] = set()
    for path in sorted(SOURCE.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - not ours to fix
            continue
        for node in tree.body:
            names: list[str] = []
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for name in names:
                if not _CACHEY.search(name):
                    continue
                value = node.value
                container = isinstance(value, ast.Dict) or (
                    isinstance(value, ast.Call)
                    and getattr(value.func, "id", "")
                    in ("dict", "OrderedDict", "defaultdict")
                )
                if container:
                    found.add(name)
    return found


class TestTheMapIsComplete:
    def test_every_cache_is_classified(self):
        unclassified = sorted(_module_level_caches() - set(CACHES))
        assert not unclassified, (
            f"{unclassified} are module-level caches nobody has said whether "
            "they hold per-person content. If they do, the user belongs in "
            "the key; if not, say so here."
        )

    def test_the_map_has_no_ghosts(self):
        gone = sorted(set(CACHES) - _module_level_caches())
        assert not gone, f"{gone} are in the map and no longer exist"

    @pytest.mark.parametrize("name", sorted(CACHES))
    def test_each_entry_says_something(self, name):
        assert len(CACHES[name]) > 40, name


class TestTheUserIsActuallyInTheKey:
    """Read from the source, not from the map."""

    def test_the_mcp_tool_cache(self):
        source = (SOURCE / "aegra" / "mcp.py").read_text()
        assert 'cache_key: str | None = f"{user_id}:{server_key}"' in source

    def test_the_ldap_membership_cache(self):
        source = (SOURCE / "src" / "ldap" / "service.py").read_text()
        assert 'f"ldap:membership:{user_id}:{group_cn}"' in source

    def test_the_graph_fingerprint_takes_the_user(self):
        import inspect

        from agent.aegra.graph import _graph_fingerprint

        assert "user_identity" in inspect.signature(_graph_fingerprint).parameters
