"""Remembered facts, and where each one came from."""

from __future__ import annotations

import pytest

from agent.src.memory.provenance import Fact, Recollection

FACT = Fact(text="prefers short answers", source_thread="t1", noted_at="2026-10-20")


def recollection(*facts: Fact) -> Recollection:
    return Recollection(list(facts) or [FACT])


def test_a_remembered_fact_can_be_listed():
    assert recollection().facts()[0].text == "prefers short answers"


def test_every_fact_says_where_it_came_from():
    assert recollection().facts()[0].source_thread == "t1"


def test_a_fact_without_a_source_is_refused():
    with pytest.raises(ValueError):
        Fact(text="from nowhere", source_thread="", noted_at="2026-10-20")


def test_an_empty_fact_is_refused():
    with pytest.raises(ValueError):
        Fact(text="   ", source_thread="t1", noted_at="2026-10-20")


def test_a_fact_can_be_forgotten():
    r = recollection()
    r.forget("prefers short answers")
    assert r.facts() == []


def test_forgetting_something_unremembered_is_harmless():
    r = recollection()
    r.forget("never said this")
    assert len(r.facts()) == 1


def test_the_same_fact_is_not_remembered_twice():
    r = recollection()
    r.remember(
        Fact(text="prefers short answers", source_thread="t2", noted_at="2026-10-21")
    )
    assert len(r.facts()) == 1


def test_remembering_keeps_the_first_source():
    r = recollection()
    r.remember(
        Fact(text="prefers short answers", source_thread="t2", noted_at="2026-10-21")
    )
    assert r.facts()[0].source_thread == "t1"


def test_facts_are_rendered_as_notes_rather_than_orders():
    rendered = recollection().as_prompt_section()
    assert "prefers short answers" in rendered
    assert "instruction" not in rendered.lower()


def test_the_rendering_says_these_are_things_to_know():
    assert "know" in recollection().as_prompt_section().lower()


def test_nothing_is_rendered_when_nothing_is_remembered():
    assert Recollection([]).as_prompt_section() == ""
