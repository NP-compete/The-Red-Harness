"""A forked conversation stays in the list it was forked from."""

from __future__ import annotations

from agent.aegra.fork_routes import _fork_metadata


def test_carries_the_identity_the_list_is_searched_by():
    """Without it the fork exists, is owned, and is never listed."""
    source = {"user_identity": "johnwick", "graph_id": "agent"}
    assert (
        _fork_metadata(
            source, title="X (fork)", thread_id="p1", checkpoint=None, message_count=1
        )["user_identity"]
        == "johnwick"
    )


def test_carries_the_owner():
    source = {"owner": "dev-user"}
    assert (
        _fork_metadata(
            source, title="X", thread_id="p1", checkpoint=None, message_count=1
        )["owner"]
        == "dev-user"
    )


def test_says_what_it_was_forked_from():
    meta = _fork_metadata(
        {}, title="X", thread_id="p1", checkpoint="c1", message_count=3
    )
    assert meta["forked_from"] == "p1"
    assert meta["forked_at_checkpoint"] == "c1"
    assert meta["forked_message_count"] == 3


def test_keeps_the_graph_and_assistant_so_the_copy_can_run():
    source = {"graph_id": "g", "assistant_id": "a"}
    meta = _fork_metadata(
        source, title="X", thread_id="p1", checkpoint=None, message_count=1
    )
    assert meta["graph_id"] == "g"
    assert meta["assistant_id"] == "a"


def test_falls_back_when_the_source_names_no_graph():
    meta = _fork_metadata(
        {}, title="X", thread_id="p1", checkpoint=None, message_count=1
    )
    assert meta["graph_id"] == "agent"


def test_lands_in_the_same_project():
    source = {"project_id": "p-7"}
    assert (
        _fork_metadata(
            source, title="X", thread_id="p1", checkpoint=None, message_count=1
        )["project_id"]
        == "p-7"
    )


def test_leaves_out_an_identity_the_source_did_not_have():
    meta = _fork_metadata(
        {}, title="X", thread_id="p1", checkpoint=None, message_count=1
    )
    assert "user_identity" not in meta
