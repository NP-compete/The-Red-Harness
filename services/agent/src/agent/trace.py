"""Turning recorded spans into a tree someone can read."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SECRETISH = re.compile(r"(?i)(key|token|secret|password|passwd|credential)")


@dataclass(frozen=True)
class Span:
    """One span of a trace."""

    span_id: str
    parent_id: str | None
    name: str
    start_ms: float
    end_ms: float
    attributes: dict[str, str]

    def __post_init__(self) -> None:
        """Reject a span with no id, or one ending before it starts."""
        if not self.span_id.strip():
            raise ValueError("a span must have an identifier")
        if self.end_ms < self.start_ms:
            raise ValueError("a span cannot end before it starts")


@dataclass(frozen=True)
class Node:
    """One span in the assembled tree, with its children and own time."""

    span_id: str
    name: str
    duration_ms: float
    own_ms: float
    attributes: dict[str, str]
    children: tuple["Node", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Trace:
    """The assembled span tree, and the spans that had no parent."""

    roots: tuple[Node, ...]
    orphans: tuple[str, ...]
    total_ms: float
    slowest: str


def build_trace(spans: list[Span]) -> Trace:
    """Assemble `spans` into a tree, rejecting duplicates and loops."""
    if not spans:
        raise ValueError("there is nothing to trace")

    ids = [span.span_id for span in spans]
    if len(ids) != len(set(ids)):
        raise ValueError("a span cannot appear twice")

    by_id = {span.span_id: span for span in spans}
    _refuse_loops(by_id)

    children: dict[str | None, list[Span]] = {}
    orphans: list[str] = []
    for span in spans:
        parent = span.parent_id if span.parent_id in by_id else None
        if span.parent_id is not None and parent is None:
            orphans.append(span.span_id)
        children.setdefault(parent, []).append(span)

    roots = tuple(_node(span, children) for span in _ordered(children.get(None, [])))

    nodes: list[Node] = []
    _collect(roots, nodes)
    slowest = max(nodes, key=lambda node: node.own_ms).span_id

    return Trace(
        roots=roots,
        orphans=tuple(sorted(orphans)),
        total_ms=max(node.duration_ms for node in roots),
        slowest=slowest,
    )


def _node(span: Span, children: dict[str | None, list[Span]]) -> Node:
    """Build the node for `span` and everything under it."""
    kids = tuple(
        _node(child, children) for child in _ordered(children.get(span.span_id, []))
    )
    duration = span.end_ms - span.start_ms
    return Node(
        span_id=span.span_id,
        name=span.name,
        duration_ms=duration,
        own_ms=duration - sum(kid.duration_ms for kid in kids),
        attributes={
            key: value
            for key, value in span.attributes.items()
            if not SECRETISH.search(key)
        },
        children=kids,
    )


def _ordered(spans: list[Span]) -> list[Span]:
    """Spans in start order, ties broken by id."""
    return sorted(spans, key=lambda span: (span.start_ms, span.span_id))


def _collect(nodes: tuple[Node, ...], into: list[Node]) -> None:
    """Append every node under `nodes` into `into`."""
    for node in nodes:
        into.append(node)
        _collect(node.children, into)


def _refuse_loops(by_id: dict[str, Span]) -> None:
    """Raise if any span is its own ancestor."""
    for span in by_id.values():
        seen = {span.span_id}
        parent = span.parent_id
        while parent is not None and parent in by_id:
            if parent in seen:
                raise ValueError("these spans are their own ancestors")
            seen.add(parent)
            parent = by_id[parent].parent_id
