"""What a run actually changed in the world."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.agent.side_effects import Effect, summarise_effects


def effect(**kwargs) -> Effect:
    defaults = {
        "kind": "file-written",
        "target": "out/report.md",
        "reversible": True,
        "undo_hint": "delete the file",
        "cost": Decimal("0"),
    }
    defaults.update(kwargs)
    return Effect(**defaults)


def test_a_run_that_changed_nothing_says_so():
    assert summarise_effects([]).changed_anything is False


def test_a_run_that_changed_nothing_has_a_plain_summary():
    assert summarise_effects([]).summary == "Nothing was changed"


def test_effects_are_counted():
    assert summarise_effects([effect(), effect(target="out/data.csv")]).count == 2


def test_effects_are_grouped_by_what_was_done():
    effects = [
        effect(),
        effect(target="out/b.md"),
        effect(kind="email-sent", target="ana"),
    ]
    grouped = summarise_effects(effects).by_kind
    assert grouped["file-written"] == ("out/b.md", "out/report.md")


def test_the_summary_reads_plainly():
    effects = [
        effect(),
        effect(target="out/b.md"),
        effect(kind="email-sent", target="ana"),
    ]
    assert summarise_effects(effects).summary == "2 files written, 1 email sent"


def test_a_single_effect_is_described_in_the_singular():
    assert summarise_effects([effect()]).summary == "1 file written"


def test_effects_that_cannot_be_undone_are_called_out():
    sent = effect(kind="email-sent", target="ana", reversible=False, undo_hint="")
    assert summarise_effects([sent]).permanent == ("email-sent: ana",)


def test_reversible_effects_are_not_called_permanent():
    assert summarise_effects([effect()]).permanent == ()


def test_a_run_with_anything_permanent_cannot_be_fully_undone():
    sent = effect(kind="email-sent", reversible=False, undo_hint="")
    assert summarise_effects([effect(), sent]).fully_reversible is False


def test_a_run_of_reversible_effects_can_be_undone():
    assert summarise_effects([effect(), effect(target="b")]).fully_reversible is True


def test_how_to_undo_each_reversible_effect_is_kept():
    assert summarise_effects([effect()]).undo_steps == ("delete the file",)


def test_nothing_is_offered_to_undo_what_cannot_be_undone():
    sent = effect(kind="email-sent", reversible=False, undo_hint="")
    assert summarise_effects([sent]).undo_steps == ()


def test_what_the_run_cost_is_totalled():
    paid = [effect(cost=Decimal("1.50")), effect(cost=Decimal("0.25"), target="b")]
    assert summarise_effects(paid).cost == Decimal("1.75")


def test_a_free_run_costs_nothing():
    assert summarise_effects([effect()]).cost == Decimal("0.00")


def test_the_same_thing_touched_twice_is_listed_once():
    assert summarise_effects([effect(), effect()]).by_kind["file-written"] == (
        "out/report.md",
    )


def test_the_same_thing_touched_twice_still_counts_as_one_change():
    assert summarise_effects([effect(), effect()]).count == 1


def test_a_reversible_effect_without_a_way_back_is_refused():
    with pytest.raises(ValueError):
        Effect(
            kind="file-written",
            target="a",
            reversible=True,
            undo_hint="",
            cost=Decimal("0"),
        )


def test_an_effect_without_a_target_is_refused():
    with pytest.raises(ValueError):
        effect(target="  ")


def test_a_negative_cost_is_refused():
    with pytest.raises(ValueError):
        effect(cost=Decimal("-1"))
