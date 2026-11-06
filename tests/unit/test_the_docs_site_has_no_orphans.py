"""Every doc is reachable from the index, and every link resolves.

`docs/` is published as GitHub Pages, and a page nothing links to
is a page nobody opens — the same disease as the test folders that
were in no CI job, in a place where it is even quieter, because a
broken docs site fails nothing.

Both directions matter. A doc missing from `index.md` is invisible;
a link in `index.md` to a file that moved is a 404 on the site and
reads fine in review.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
INDEX = DOCS / "index.md"

#: Markdown links that point at a path, not a URL or an anchor.
LINK = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")


def _pages() -> set[str]:
    return {
        str(path.relative_to(DOCS))
        for path in DOCS.rglob("*.md")
        if path.name != "index.md" and not path.name.startswith("_")
    }


def _linked() -> set[str]:
    return {
        link.split("#", 1)[0]
        for link in LINK.findall(INDEX.read_text(encoding="utf-8"))
        if link.split("#", 1)[0]
    }


def test_there_are_pages_to_check():
    """A glob matching nothing would pass both assertions below."""
    assert len(_pages()) > 5


def test_the_index_exists():
    assert INDEX.is_file(), f"{INDEX} is the site's landing page"


def test_every_page_is_linked_from_the_index():
    orphans = sorted(_pages() - _linked())
    assert not orphans, (
        f"these are published and linked from nowhere: {orphans}. "
        "Add them to docs/index.md, or delete them."
    )


def test_every_index_link_resolves():
    broken = sorted(one for one in _linked() if not (DOCS / one).exists())
    assert not broken, (
        f"docs/index.md links to {broken}, which do not exist — "
        "a 404 on the site that reads fine in a diff."
    )


def test_links_inside_the_docs_resolve_too():
    broken: dict[str, list[str]] = {}
    for page in DOCS.rglob("*.md"):
        here = page.parent
        missing = [
            link
            for raw in LINK.findall(page.read_text(encoding="utf-8"))
            if (link := raw.split("#", 1)[0])
            and not (here / link).exists()
            and not (ROOT / link).exists()
        ]
        if missing:
            broken[str(page.relative_to(ROOT))] = sorted(set(missing))
    assert not broken, f"links pointing at nothing: {broken}"
