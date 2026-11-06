"""Not running a suite against an agent that can change things."""

from __future__ import annotations

import pytest

from scripts.bench.guard import BenchRefused, check_safe_to_run


class TestAnAgentThatCanChangeThings:
    def test_it_is_refused(self):
        with pytest.raises(BenchRefused):
            check_safe_to_run(effects="live")

    def test_the_refusal_names_the_setting(self):
        with pytest.raises(BenchRefused, match="effects"):
            check_safe_to_run(effects="live")

    def test_the_refusal_says_what_it_should_be(self):
        with pytest.raises(BenchRefused, match="dry_run"):
            check_safe_to_run(effects="live")


class TestAnAgentThatCannot:
    def test_a_dry_run_agent_is_allowed(self):
        assert check_safe_to_run(effects="dry_run") is None


class TestAnAgentThatWillNotSay:
    @pytest.mark.parametrize("effects", ["", None, "something_new"])
    def test_it_is_refused_rather_than_assumed_safe(self, effects):
        with pytest.raises(BenchRefused):
            check_safe_to_run(effects=effects)

    def test_the_refusal_says_it_could_not_tell(self):
        with pytest.raises(BenchRefused, match="could not"):
            check_safe_to_run(effects="")


class TestItRunsBeforeAnythingElse:
    def test_the_entry_point_checks_before_the_first_task(self):
        from scripts.bench.preflight import preflight

        found = preflight(suite="jb", url="http://x", effects="live", model="")
        assert found[0].name == "agent"
        assert not found[0].ok

    def test_a_refusal_exits_non_zero(self, monkeypatch, capsys):
        from scripts.bench.__main__ import main

        monkeypatch.setattr("scripts.bench.__main__._effects_of", lambda _url: "live")
        assert main(["--suite", "jb"]) != 0

    def test_the_reason_reaches_the_terminal(self, monkeypatch, capsys):
        from scripts.bench.__main__ import main

        monkeypatch.setattr("scripts.bench.__main__._effects_of", lambda _url: "live")
        main(["--suite", "jb"])
        assert "effects" in capsys.readouterr().err


class TestAnEntryPointThatRanNothing:
    """A bench command that exits zero having run no tasks is the"""

    def test_it_does_not_report_success(self, monkeypatch):
        from scripts.bench.__main__ import main

        monkeypatch.setattr(
            "scripts.bench.__main__._effects_of", lambda _url: "dry_run"
        )
        assert main(["--suite", "jb"]) != 0

    def test_it_says_what_is_missing(self, monkeypatch, capsys):
        from scripts.bench.__main__ import main

        monkeypatch.setattr(
            "scripts.bench.__main__._effects_of", lambda _url: "dry_run"
        )
        main(["--suite", "jb"])
        assert "not" in capsys.readouterr().err.lower()
