"""Where this package sits, worked out once.

Twelve modules used to count `.parent` hops out to the repository
root by hand. Moving the package one directory deeper broke all
twelve at once, and the symptom was a config file "not found" at a
path with `services/` in the wrong place. One import is cheaper
than twelve counts that have to agree.
"""

from __future__ import annotations

from pathlib import Path

#: `<repo>/services/agent` in a checkout, `/app/agent` in the image.
PACKAGE_ROOT = Path(__file__).resolve().parent

#: What `sys.path` needs for `agent.*` to import.
SERVICES_ROOT = PACKAGE_ROOT.parent


def _repo_root() -> Path:
    """The directory holding `config/` and `pyproject.toml`.

    Found rather than counted. The image copies `services/agent`
    to `/app/agent`, one level shallower than the checkout, so a
    fixed number of `.parent` hops is right in exactly one of the
    two places it runs — and the way it fails is a config path
    that resolves to `/config/agent` and an agent that silently
    loads defaults.
    """
    for candidate in (PACKAGE_ROOT, *PACKAGE_ROOT.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return SERVICES_ROOT.parent


#: `<repo>` — holds `config/`, `deployment/`, `pyproject.toml`.
REPO_ROOT = _repo_root()

#: `<repo>/config/agent`, the default when `CONFIG_PATH` is unset.
CONFIG_ROOT = REPO_ROOT / "config" / "agent"
