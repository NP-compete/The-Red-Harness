"""What happens when a declared extension cannot be loaded."""

from __future__ import annotations

import pytest

from agent.src.infrastructure.extensions import (
    ExtensionUnavailable,
    declared_extension,
)


class TestHowAnExtensionIsDeclared:
    def test_a_bare_path_is_an_extension(self):
        assert declared_extension("pkg.mod:Thing").path == "pkg.mod:Thing"

    def test_a_bare_path_refuses_to_run_without_it(self):
        assert declared_extension("pkg.mod:Thing").required is True

    def test_a_deployment_can_say_it_is_optional(self):
        entry = {"path": "pkg.mod:Thing", "on_failure": "open"}
        assert declared_extension(entry).required is False

    def test_a_deployment_can_say_it_is_required(self):
        entry = {"path": "pkg.mod:Thing", "on_failure": "closed"}
        assert declared_extension(entry).required is True

    def test_an_unknown_failure_mode_is_refused_rather_than_guessed(self):
        with pytest.raises(ValueError, match="on_failure"):
            declared_extension({"path": "pkg.mod:Thing", "on_failure": "maybe"})

    def test_an_entry_with_no_path_is_refused(self):
        with pytest.raises(ValueError, match="path"):
            declared_extension({"on_failure": "open"})

    def test_a_path_without_an_attribute_is_refused(self):
        """`module:Attr` or nothing: a bare module names no extension."""
        with pytest.raises(ValueError, match="module:"):
            declared_extension("pkg.mod")


class TestWhenOneCannotBeLoaded:
    def test_a_required_extension_stops_the_agent(self):
        with pytest.raises(ExtensionUnavailable, match="nonexistent.module:Thing"):
            declared_extension("nonexistent.module:Thing").load()

    def test_the_refusal_says_why(self):
        with pytest.raises(ExtensionUnavailable, match="could not be loaded"):
            declared_extension("nonexistent.module:Thing").load()

    def test_an_optional_extension_is_skipped(self):
        entry = {"path": "nonexistent.module:Thing", "on_failure": "open"}
        assert declared_extension(entry).load() is None

    def test_one_that_loads_is_returned(self):
        made = declared_extension("json:JSONDecoder").load()
        assert made is not None


class TestHowTheyReachTheRun:
    """`extra_middleware` is the seam; these are its two outcomes."""

    @staticmethod
    def _build(paths: list) -> list:
        from unittest.mock import patch

        from agent.src.infrastructure import middleware as mw

        resolved = type(
            "R",
            (),
            {
                "extra_middleware": paths,
                "summarization_tool_enabled": False,
                "model_call_limit": type("L", (), {"enabled": False})(),
                "tool_call_limit": type("L", (), {"enabled": False})(),
                "tool_exclusion": type("L", (), {"enabled": False})(),
                "model_retry": type("L", (), {"enabled": False})(),
                "model_fallback": type("L", (), {"enabled": False})(),
                "tool_retry": type("L", (), {"enabled": False})(),
                "tool_output": type("L", (), {"enabled": False})(),
            },
        )()
        with patch.object(mw, "_append_guardrails"):
            return mw.build_middleware_list(resolved)

    def test_a_missing_required_extension_refuses_to_build(self):
        with pytest.raises(ExtensionUnavailable):
            self._build(["nonexistent.module:Thing"])

    def test_a_missing_optional_extension_is_skipped(self):
        built = self._build(
            [{"path": "nonexistent.module:Thing", "on_failure": "open"}]
        )
        assert isinstance(built, list)

    def test_a_deployment_that_declares_none_is_unaffected(self):
        assert isinstance(self._build([]), list)


class TestReportingWithoutRaising:
    """A page describing extensions must render even when one is broken."""

    def test_one_that_loads_reports_no_problem(self):
        loaded, problem = declared_extension("json:JSONDecoder").status()
        assert loaded is True and problem == ""

    def test_a_missing_required_one_reports_rather_than_raises(self):
        loaded, problem = declared_extension("nowhere.at.all:Thing").status()
        assert loaded is False and "nowhere" in problem

    def test_a_missing_optional_one_reports_the_same_way(self):
        entry = {"path": "nowhere.at.all:Thing", "on_failure": "open"}
        loaded, problem = declared_extension(entry).status()
        assert loaded is False and problem
