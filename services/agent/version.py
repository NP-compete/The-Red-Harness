"""One version, named in one place (E28-T11, E10 strand D)."""

from __future__ import annotations

from agent._root import REPO_ROOT

DISTRIBUTION = "template-agent"
UNKNOWN = "unknown"


def version() -> str:
    """This build's version, or `unknown` rather than a guess."""
    import os

    named = os.environ.get("APPLICATION_VERSION", "").strip()
    if named:
        return named
    try:
        from importlib.metadata import version as installed

        return installed(DISTRIBUTION)
    except Exception:  # noqa: BLE001 - PackageNotFoundError and anything else
        pass
    return _from_pyproject() or UNKNOWN


def _from_pyproject() -> str:
    """The working tree's own answer, for a checkout nobody installed."""
    here = REPO_ROOT / "pyproject.toml"
    if not here.is_file():
        return ""
    try:
        import tomllib

        return str(
            (tomllib.loads(here.read_text()).get("project") or {}).get("version") or ""
        )
    except Exception:  # noqa: BLE001
        return ""


def same_as(theirs: str) -> bool:
    """Whether a reported version matches this one."""
    mine = version()
    if not theirs or theirs == UNKNOWN or mine == UNKNOWN:
        return True
    return mine == theirs
