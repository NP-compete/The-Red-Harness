"""Building a set of cases to test against, out of real runs."""

from __future__ import annotations

import pytest

from agent.src.evals.dataset import Candidate, build_dataset


def candidate(case_id: str, **kwargs) -> Candidate:
    defaults = {
        "question": f"question {case_id}",
        "expected": "an answer",
        "consented": True,
        "contains_personal_data": False,
        "labelled_by": "ana",
    }
    defaults.update(kwargs)
    return Candidate(case_id=case_id, **defaults)


def test_consented_cases_are_included():
    assert build_dataset([candidate("a")], holdout=0).count == 1


def test_a_case_without_consent_is_left_out():
    built = build_dataset([candidate("a", consented=False)], holdout=0)
    assert built.count == 0


def test_a_case_left_out_for_consent_is_reported():
    built = build_dataset([candidate("a", consented=False)], holdout=0)
    assert built.excluded["no-consent"] == ("a",)


def test_a_case_with_personal_data_is_left_out():
    built = build_dataset([candidate("a", contains_personal_data=True)], holdout=0)
    assert built.excluded["personal-data"] == ("a",)


def test_a_case_nobody_labelled_is_left_out():
    built = build_dataset([candidate("a", labelled_by="")], holdout=0)
    assert built.excluded["unlabelled"] == ("a",)


def test_two_cases_asking_the_same_thing_are_collapsed():
    cases = [candidate("a", question="same"), candidate("b", question="same")]
    assert build_dataset(cases, holdout=0).count == 1


def test_a_collapsed_duplicate_is_reported():
    cases = [candidate("a", question="same"), candidate("b", question="same")]
    assert build_dataset(cases, holdout=0).excluded["duplicate"] == ("b",)


def test_a_holdout_is_set_aside():
    cases = [candidate(str(n)) for n in range(10)]
    built = build_dataset(cases, holdout=0.2, seed=1)
    assert len(built.holdout) == 2


def test_the_rest_is_available_for_tuning():
    cases = [candidate(str(n)) for n in range(10)]
    built = build_dataset(cases, holdout=0.2, seed=1)
    assert len(built.working) == 8


def test_nothing_is_in_both_halves():
    cases = [candidate(str(n)) for n in range(10)]
    built = build_dataset(cases, holdout=0.2, seed=1)
    assert set(built.working) & set(built.holdout) == set()


def test_the_same_seed_splits_the_same_way():
    cases = [candidate(str(n)) for n in range(10)]
    first = build_dataset(cases, holdout=0.2, seed=1)
    second = build_dataset(cases, holdout=0.2, seed=1)
    assert first.holdout == second.holdout


def test_a_different_seed_splits_differently():
    cases = [candidate(str(n)) for n in range(20)]
    first = build_dataset(cases, holdout=0.25, seed=1)
    second = build_dataset(cases, holdout=0.25, seed=2)
    assert first.holdout != second.holdout


def test_a_holdout_always_keeps_at_least_one_case_when_asked_for():
    cases = [candidate(str(n)) for n in range(3)]
    assert len(build_dataset(cases, holdout=0.1, seed=1).holdout) == 1


def test_a_dataset_too_small_to_split_is_reported():
    built = build_dataset([candidate("a")], holdout=0.2, seed=1)
    assert built.too_small is True


def test_a_reasonable_dataset_is_not_too_small():
    cases = [candidate(str(n)) for n in range(30)]
    assert build_dataset(cases, holdout=0.2, seed=1).too_small is False


def test_a_dataset_with_nothing_usable_is_refused():
    with pytest.raises(ValueError):
        build_dataset([candidate("a", consented=False)], holdout=0, strict=True)


def test_an_impossible_holdout_is_refused():
    with pytest.raises(ValueError):
        build_dataset([candidate("a")], holdout=1.5)


def test_a_case_without_a_question_is_refused():
    with pytest.raises(ValueError):
        candidate("a", question="  ")
