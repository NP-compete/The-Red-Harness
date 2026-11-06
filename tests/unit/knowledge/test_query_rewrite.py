"""Turning what someone asked into what to search for."""

from __future__ import annotations

import pytest

from agent.src.knowledge.query_rewrite import Glossary, rewrite_query

GLOSSARY = Glossary(
    expansions={
        "pto": ("paid time off", "annual leave"),
        "wfh": ("working from home",),
    },
    stopwords=("please", "could", "you", "tell", "me", "about", "the", "what", "is"),
)


def test_a_plain_query_is_left_alone():
    assert rewrite_query("expense policy", glossary=GLOSSARY).query == "expense policy"


def test_politeness_is_stripped_out():
    result = rewrite_query(
        "could you please tell me about the expense policy", glossary=GLOSSARY
    )
    assert result.query == "expense policy"


def test_an_acronym_is_expanded():
    result = rewrite_query("pto policy", glossary=GLOSSARY)
    assert "paid time off" in result.query


def test_the_original_acronym_is_kept_as_well():
    assert "pto" in rewrite_query("pto policy", glossary=GLOSSARY).query


def test_every_expansion_of_an_acronym_is_used():
    result = rewrite_query("pto policy", glossary=GLOSSARY)
    assert "annual leave" in result.query


def test_what_was_expanded_is_recorded():
    assert rewrite_query("pto policy", glossary=GLOSSARY).expanded == ("pto",)


def test_nothing_is_recorded_when_nothing_was_expanded():
    assert rewrite_query("expense policy", glossary=GLOSSARY).expanded == ()


def test_what_was_removed_is_recorded():
    result = rewrite_query("please tell me the expense policy", glossary=GLOSSARY)
    assert set(result.removed) == {"please", "tell", "me", "the"}


def test_a_query_of_only_filler_keeps_something_to_search_for():
    result = rewrite_query("could you please tell me", glossary=GLOSSARY)
    assert result.query != ""


def test_a_query_of_only_filler_says_it_was_too_vague():
    assert (
        rewrite_query("could you please tell me", glossary=GLOSSARY).too_vague is True
    )


def test_an_ordinary_query_is_not_too_vague():
    assert rewrite_query("expense policy", glossary=GLOSSARY).too_vague is False


def test_the_original_question_is_kept_for_the_record():
    asked = "could you please tell me about the expense policy"
    assert rewrite_query(asked, glossary=GLOSSARY).original == asked


def test_case_does_not_prevent_an_expansion():
    assert "paid time off" in rewrite_query("PTO policy", glossary=GLOSSARY).query


def test_punctuation_does_not_prevent_an_expansion():
    assert "working from home" in rewrite_query("wfh?", glossary=GLOSSARY).query


def test_a_word_appearing_twice_is_searched_for_once():
    assert rewrite_query("policy policy", glossary=GLOSSARY).query == "policy"


def test_an_empty_question_is_refused():
    with pytest.raises(ValueError):
        rewrite_query("   ", glossary=GLOSSARY)


def test_an_expansion_to_nothing_is_refused():
    with pytest.raises(ValueError):
        Glossary(expansions={"pto": ()}, stopwords=())
