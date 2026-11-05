"""Small structured things the agent writes down."""

from __future__ import annotations

import pytest

from agent.src.knowledge.artifacts import ArtifactStore, Owner

ME = Owner(subject="me@example.com", teams=("sre",))
YOU = Owner(subject="you@example.com", teams=("sre",))
OUTSIDER = Owner(subject="out@example.com", teams=("finance",))


def store(**kwargs) -> ArtifactStore:
    defaults = {"max_bytes_per_owner": 1000, "max_bytes_per_value": 200}
    defaults.update(kwargs)
    return ArtifactStore(**defaults)


def test_what_is_written_can_be_read_back():
    s = store()
    s.put(ME, key="checklist", value="step one")
    assert s.get(ME, key="checklist") == "step one"


def test_one_person_cannot_read_another_private_artifact():
    s = store()
    s.put(ME, key="checklist", value="step one")
    assert s.get(YOU, key="checklist") is None


def test_a_team_artifact_is_readable_by_the_team():
    s = store()
    s.put(ME, key="runbook", value="steps", team="sre")
    assert s.get(YOU, key="runbook", team="sre") == "steps"


def test_a_team_artifact_is_not_readable_outside_the_team():
    s = store()
    s.put(ME, key="runbook", value="steps", team="sre")
    assert s.get(OUTSIDER, key="runbook", team="sre") is None


def test_writing_to_a_team_you_are_not_in_is_refused():
    with pytest.raises(PermissionError):
        store().put(OUTSIDER, key="runbook", value="steps", team="sre")


def test_a_value_bigger_than_the_cap_is_refused():
    with pytest.raises(ValueError):
        store(max_bytes_per_value=5).put(ME, key="k", value="far too long")


def test_an_owner_cannot_exceed_their_total():
    s = store(max_bytes_per_owner=10, max_bytes_per_value=10)
    s.put(ME, key="a", value="12345")
    with pytest.raises(ValueError):
        s.put(ME, key="b", value="123456")


def test_overwriting_frees_the_space_it_used():
    s = store(max_bytes_per_owner=10, max_bytes_per_value=10)
    s.put(ME, key="a", value="1234567890")
    s.put(ME, key="a", value="1")
    s.put(ME, key="b", value="123456")
    assert s.get(ME, key="b") == "123456"


def test_deleting_frees_space_too():
    s = store(max_bytes_per_owner=10, max_bytes_per_value=10)
    s.put(ME, key="a", value="1234567890")
    s.delete(ME, key="a")
    s.put(ME, key="b", value="123456")
    assert s.get(ME, key="b") == "123456"


def test_listing_shows_only_what_you_may_see():
    s = store()
    s.put(ME, key="mine", value="x")
    s.put(ME, key="ours", value="y", team="sre")
    assert sorted(s.keys(YOU)) == ["ours"]


def test_usage_is_reported_so_a_limit_is_not_a_surprise():
    s = store()
    s.put(ME, key="a", value="12345")
    assert s.usage(ME) == 5
