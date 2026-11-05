"""What the improvement loop tried to do is kept, refusals included (E12-T8)."""

from __future__ import annotations

import pytest

from agent.src.improvement.record import (
    MAX_KEYS,
    changed_keys,
    record_proposal,
)


@pytest.fixture
def recorded(monkeypatch):
    """Every audit event this emits, in order."""
    seen: list[tuple[object, dict]] = []

    import agent.src.audit as audit

    monkeypatch.setattr(
        audit, "emit_audit_event", lambda kind, **rest: seen.append((kind, rest))
    )
    return seen


class TestWhichSettingsMoved:
    def test_a_changed_leaf_is_named_by_its_path(self):
        assert changed_keys({"a": {"b": 1}}, {"a": {"b": 2}}) == ["a.b"]

    def test_an_unchanged_leaf_is_not(self):
        assert changed_keys({"a": {"b": 1}}, {"a": {"b": 1}}) == []

    def test_a_removed_setting_counts_as_a_change(self):
        assert changed_keys({"deny": ["x"]}, {}) == ["deny"]

    def test_an_added_setting_counts_too(self):
        assert changed_keys({}, {"deny": ["x"]}) == ["deny"]


class TestTheTrail:
    def test_a_permitted_proposal_is_recorded(self, recorded):
        record_proposal(before={"prompt": "a"}, after={"prompt": "b"}, permitted=True)
        kind, details = recorded[0]
        assert str(kind.value if hasattr(kind, "value") else kind).endswith("weighed")
        assert details["keys"] == ["prompt"]
        assert details["permitted"] is True

    def test_a_refusal_is_recorded_with_its_reason(self, recorded):
        record_proposal(
            before={"human_approval": {"mode": "all"}},
            after={"human_approval": {"mode": "none"}},
            permitted=False,
            reason="human_approval.mode widens all to none",
        )
        _, details = recorded[0]
        assert details["permitted"] is False
        assert "widens all to none" in details["reason"]

    def test_the_values_are_not_in_the_trail(self, recorded):
        record_proposal(
            before={"model": {"base_url": "https://old.example/v1"}},
            after={"model": {"base_url": "https://secret.internal/v1"}},
            permitted=True,
        )
        _, details = recorded[0]
        assert "secret.internal" not in repr(details)
        assert details["keys"] == ["model.base_url"]

    def test_a_huge_rewrite_is_truncated_but_counted(self, recorded):
        before = {f"k{i}": i for i in range(MAX_KEYS + 10)}
        after = {f"k{i}": i + 1 for i in range(MAX_KEYS + 10)}
        record_proposal(before=before, after=after, permitted=True)
        _, details = recorded[0]
        assert len(details["keys"]) == MAX_KEYS
        assert details["keys_total"] == MAX_KEYS + 10

    def test_a_broken_trail_does_not_cost_the_verdict(self, monkeypatch):
        import agent.src.audit as audit

        def explode(*_args, **_rest):
            raise RuntimeError("the audit sink is down")

        monkeypatch.setattr(audit, "emit_audit_event", explode)
        record_proposal(before={"a": 1}, after={"a": 2}, permitted=False, reason="no")
