"""Turning recorded spans into a tree someone can read."""

from __future__ import annotations

import pytest

from agent.src.agent.trace import Span, build_trace


def span(span_id: str, parent: str | None = None, **kwargs) -> Span:
    defaults = {
        "name": f"step {span_id}",
        "start_ms": 0.0,
        "end_ms": 10.0,
        "attributes": {},
    }
    defaults.update(kwargs)
    return Span(span_id=span_id, parent_id=parent, **defaults)


def test_a_single_span_is_the_root():
    trace = build_trace([span("a")])
    assert trace.roots[0].span_id == "a"


def test_a_child_hangs_off_its_parent():
    trace = build_trace([span("a"), span("b", parent="a")])
    assert [child.span_id for child in trace.roots[0].children] == ["b"]


def test_children_are_ordered_by_when_they_started():
    spans = [
        span("a"),
        span("late", parent="a", start_ms=5.0, end_ms=6.0),
        span("early", parent="a", start_ms=1.0, end_ms=2.0),
    ]
    trace = build_trace(spans)
    assert [child.span_id for child in trace.roots[0].children] == ["early", "late"]


def test_how_long_each_span_took_is_worked_out():
    trace = build_trace([span("a", start_ms=2.0, end_ms=12.0)])
    assert trace.roots[0].duration_ms == 10.0


def test_time_not_spent_in_children_is_reported():
    spans = [span("a", end_ms=10.0), span("b", parent="a", start_ms=1.0, end_ms=4.0)]
    trace = build_trace(spans)
    assert trace.roots[0].own_ms == 7.0


def test_a_span_with_no_children_spends_all_its_time_itself():
    assert build_trace([span("a")]).roots[0].own_ms == 10.0


def test_the_slowest_span_is_named():
    spans = [span("a", end_ms=10.0), span("slow", parent="a", start_ms=0.0, end_ms=9.0)]
    assert build_trace(spans).slowest == "slow"


def test_the_total_time_is_the_root_span():
    spans = [span("a", end_ms=10.0), span("b", parent="a", start_ms=1.0, end_ms=4.0)]
    assert build_trace(spans).total_ms == 10.0


def test_several_roots_are_all_kept():
    trace = build_trace([span("a"), span("b")])
    assert len(trace.roots) == 2


def test_a_span_whose_parent_is_missing_becomes_a_root():
    trace = build_trace([span("orphan", parent="gone")])
    assert trace.roots[0].span_id == "orphan"


def test_an_orphan_is_reported():
    assert build_trace([span("orphan", parent="gone")]).orphans == ("orphan",)


def test_a_span_that_is_its_own_parent_is_refused():
    with pytest.raises(ValueError):
        build_trace([span("a", parent="a")])


def test_a_loop_between_spans_is_refused():
    with pytest.raises(ValueError):
        build_trace([span("a", parent="b"), span("b", parent="a")])


def test_sensitive_attributes_are_not_carried_into_the_trace():
    secret = span("a", attributes={"tool": "mail", "api_key": "9f2b7c1e"})
    assert "api_key" not in build_trace([secret]).roots[0].attributes


def test_ordinary_attributes_are_kept():
    tagged = span("a", attributes={"tool": "mail"})
    assert build_trace([tagged]).roots[0].attributes == {"tool": "mail"}


def test_a_span_ending_before_it_started_is_refused():
    with pytest.raises(ValueError):
        Span(
            span_id="a",
            parent_id=None,
            name="x",
            start_ms=10.0,
            end_ms=1.0,
            attributes={},
        )


def test_a_trace_with_no_spans_is_refused():
    with pytest.raises(ValueError):
        build_trace([])


def test_two_spans_with_the_same_identifier_are_refused():
    with pytest.raises(ValueError):
        build_trace([span("a"), span("a")])
