"""What is worth doing first in an empty workspace."""

from __future__ import annotations

import pytest

from agent.src.agent.first_run import Step, Workspace, next_steps


def workspace(**kwargs) -> Workspace:
    defaults = {
        "threads": 0,
        "sources_connected": 0,
        "memories": 0,
        "members": 1,
        "may_connect_sources": True,
        "may_invite": True,
        "dismissed": (),
    }
    defaults.update(kwargs)
    return Workspace(**defaults)


def test_an_empty_workspace_is_asked_to_connect_something_first():
    assert next_steps(workspace())[0] is Step.CONNECT_SOURCE


def test_asking_a_first_question_is_offered_too():
    assert Step.ASK_SOMETHING in next_steps(workspace())


def test_a_workspace_with_a_source_no_longer_asks_for_one():
    settled = workspace(sources_connected=2)
    assert Step.CONNECT_SOURCE not in next_steps(settled)


def test_someone_who_has_asked_something_is_not_asked_again():
    used = workspace(threads=3)
    assert Step.ASK_SOMETHING not in next_steps(used)


def test_connecting_is_not_offered_to_someone_who_cannot_do_it():
    restricted = workspace(may_connect_sources=False)
    assert Step.CONNECT_SOURCE not in next_steps(restricted)


def test_a_restricted_person_is_still_invited_to_ask_something():
    restricted = workspace(may_connect_sources=False)
    assert Step.ASK_SOMETHING in next_steps(restricted)


def test_inviting_others_is_offered_once_the_workspace_is_working():
    working = workspace(threads=3, sources_connected=1)
    assert Step.INVITE_OTHERS in next_steps(working)


def test_inviting_others_is_not_offered_before_anything_works():
    assert Step.INVITE_OTHERS not in next_steps(workspace())


def test_inviting_is_not_offered_where_others_are_already_here():
    crowded = workspace(threads=3, sources_connected=1, members=4)
    assert Step.INVITE_OTHERS not in next_steps(crowded)


def test_inviting_is_not_offered_to_someone_who_cannot_invite():
    restricted = workspace(threads=3, sources_connected=1, may_invite=False)
    assert Step.INVITE_OTHERS not in next_steps(restricted)


def test_a_dismissed_step_is_not_offered_again():
    assert Step.CONNECT_SOURCE not in next_steps(
        workspace(dismissed=(Step.CONNECT_SOURCE,))
    )


def test_dismissing_one_step_leaves_the_others():
    assert Step.ASK_SOMETHING in next_steps(workspace(dismissed=(Step.CONNECT_SOURCE,)))


def test_a_workspace_that_is_fully_under_way_is_left_alone():
    settled = workspace(threads=20, sources_connected=2, memories=5, members=6)
    assert next_steps(settled) == []


def test_a_negative_count_is_refused():
    with pytest.raises(ValueError):
        workspace(threads=-1)


def test_a_workspace_with_no_members_is_refused():
    with pytest.raises(ValueError):
        workspace(members=0)
