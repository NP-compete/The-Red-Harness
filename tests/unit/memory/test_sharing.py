"""Which remembered things may be used where."""

from __future__ import annotations

import pytest

from agent.src.memory.sharing import Memory, Place, usable_here


def memory(**kwargs) -> Memory:
    defaults = {
        "key": "units",
        "text": "Metric units in every report.",
        "owner": "ada",
        "org": "northwind",
        "team": "",
        "shared_with_team": False,
        "sensitive": False,
    }
    defaults.update(kwargs)
    return Memory(**defaults)


def place(**kwargs) -> Place:
    defaults = {
        "reader": "ada",
        "org": "northwind",
        "team": "platform",
        "shared_thread": False,
    }
    defaults.update(kwargs)
    return Place(**defaults)


def test_your_own_memory_is_yours_to_use():
    assert usable_here([memory()], at=place()) == ["units"]


def test_someone_else_s_private_memory_is_not_reachable():
    assert usable_here([memory(owner="grace")], at=place()) == []


def test_a_memory_from_another_organisation_is_never_reachable():
    far = memory(org="eastwind")
    assert usable_here([far], at=place()) == []


def test_a_team_memory_is_reachable_by_the_team():
    shared = memory(owner="grace", team="platform", shared_with_team=True)
    assert usable_here([shared], at=place()) == ["units"]


def test_a_team_memory_is_not_reachable_from_another_team():
    shared = memory(owner="grace", team="payments", shared_with_team=True)
    assert usable_here([shared], at=place()) == []


def test_a_memory_marked_for_a_team_but_not_shared_stays_private():
    held = memory(owner="grace", team="platform", shared_with_team=False)
    assert usable_here([held], at=place()) == []


def test_your_own_memory_is_held_back_in_a_thread_others_can_read():
    assert usable_here([memory()], at=place(shared_thread=True)) == []


def test_a_team_memory_is_still_usable_in_a_shared_thread():
    shared = memory(owner="grace", team="platform", shared_with_team=True)
    assert usable_here([shared], at=place(shared_thread=True)) == ["units"]


def test_a_sensitive_memory_is_never_used_in_a_shared_thread():
    shared = memory(team="platform", shared_with_team=True, sensitive=True)
    assert usable_here([shared], at=place(shared_thread=True)) == []


def test_a_sensitive_memory_is_usable_in_your_own_thread():
    assert usable_here([memory(sensitive=True)], at=place()) == ["units"]


def test_a_sensitive_memory_of_someone_else_s_is_not_reachable_at_all():
    theirs = memory(
        owner="grace", team="platform", shared_with_team=True, sensitive=True
    )
    assert usable_here([theirs], at=place()) == []


def test_the_order_given_is_the_order_returned():
    first = memory(key="units")
    second = memory(key="tone")
    assert usable_here([first, second], at=place()) == ["units", "tone"]


def test_nothing_remembered_means_nothing_usable():
    assert usable_here([], at=place()) == []


def test_a_memory_with_no_key_is_refused():
    with pytest.raises(ValueError):
        memory(key="  ")
