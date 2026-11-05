"""Every change to a capability, recorded."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.src.agent.config.features import Scope
from agent.src.agent.config.flag_audit import record_flag_change


def _emitted(**kwargs):
    seen = []

    def _spy(event_type, **details):
        seen.append((event_type, details))

    with patch("agent.src.agent.config.flag_audit.emit_audit_event", side_effect=_spy):
        record_flag_change(
            key=kwargs.pop("key", "planner_enabled"),
            scope=kwargs.pop("scope", Scope.DEPLOYMENT),
            was=kwargs.pop("was", False),
            now=kwargs.pop("now", True),
            who=kwargs.pop("who", "alice"),
            **kwargs,
        )
    return seen


class TestWhatIsRecorded:
    def test_a_change_is_recorded(self):
        assert _emitted()

    def test_it_names_the_flag(self):
        _type, details = _emitted()[0]
        assert details["key"] == "planner_enabled"

    def test_it_names_who_changed_it(self):
        _type, details = _emitted()[0]
        assert details["who"] == "alice"

    def test_it_records_what_it_was(self):
        _type, details = _emitted()[0]
        assert details["was"] is False

    def test_it_records_what_it_became(self):
        _type, details = _emitted()[0]
        assert details["now"] is True

    def test_it_records_the_scope_it_was_set_at(self):
        _type, details = _emitted()[0]
        assert details["scope"] == "deployment"

    def test_the_event_says_what_kind_of_thing_happened(self):
        kind, _details = _emitted()[0]
        assert "feature" in kind and "change" in kind


class TestANoOp:
    def test_setting_it_to_what_it_already_was_is_not_a_change(self):
        assert _emitted(was=True, now=True) == []

    def test_turning_it_off_when_it_was_off_is_not_either(self):
        assert _emitted(was=False, now=False) == []

    def test_but_an_actual_change_still_is(self):
        assert _emitted(was=True, now=False)


class TestWithoutException:
    """Deployment scope is recorded even with audit switched off."""

    @staticmethod
    def _with_audit_off(scope):
        said = []
        with (
            patch(
                "agent.src.agent.config.flag_audit.is_audit_enabled",
                return_value=False,
            ),
            patch("agent.src.agent.config.flag_audit.logger") as log,
        ):
            record_flag_change(
                key="planner_enabled", scope=scope, was=False, now=True, who="alice"
            )
            said.extend(call for call in log.warning.call_args_list)
        return said

    def test_a_deployment_change_is_still_written_somewhere(self):
        assert self._with_audit_off(Scope.DEPLOYMENT)

    def test_the_fallback_still_names_the_flag(self):
        said = str(self._with_audit_off(Scope.DEPLOYMENT))
        assert "planner_enabled" in said

    def test_the_fallback_still_names_who(self):
        said = str(self._with_audit_off(Scope.DEPLOYMENT))
        assert "alice" in said

    def test_a_narrower_scope_is_not_forced_through(self):
        assert self._with_audit_off(Scope.USER) == []


class TestItNeverCostsTheChange:
    def test_an_audit_that_fails_does_not_undo_the_change(self):
        with patch(
            "agent.src.agent.config.flag_audit.emit_audit_event",
            side_effect=RuntimeError("audit sink down"),
        ):
            record_flag_change(
                key="planner_enabled",
                scope=Scope.DEPLOYMENT,
                was=False,
                now=True,
                who="alice",
            )

    def test_a_missing_identity_is_recorded_as_unknown_not_dropped(self):
        _type, details = _emitted(who="")[0]
        assert details["who"]


class TestTheRouteUsesIt:
    def test_setting_a_flag_reaches_the_recorder(self):
        import inspect

        from agent.aegra import feature_routes

        assert "record_flag_change" in inspect.getsource(feature_routes)

    @pytest.mark.parametrize("scope", [Scope.DEPLOYMENT, Scope.AGENT, Scope.USER])
    def test_every_scope_can_be_recorded(self, scope):
        assert _emitted(scope=scope)
