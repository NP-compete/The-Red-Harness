"""The orphan check has to count an import, not a word."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_unreachable_modules import imports_in  # noqa: E402


class TestWhatCountsAsReaching:
    def test_a_plain_import(self):
        assert "agent.src.security.taint" in imports_in(
            "import agent.src.security.taint"
        )

    def test_a_from_import(self):
        assert "agent.src.security.taint" in imports_in(
            "from agent.src.security.taint import TaintLedger"
        )

    def test_an_import_inside_a_function(self):
        source = "def f():\n    from agent.src.security.taint import X\n    return X"
        assert "agent.src.security.taint" in imports_in(source)

    def test_importing_the_package_and_naming_the_module(self):
        assert "agent.src.security.taint" in imports_in(
            "from agent.src.security import taint"
        )

    def test_several_on_one_line(self):
        found = imports_in("from agent.src.security import taint, rewind")
        assert {
            "agent.src.security.taint",
            "agent.src.security.rewind",
        } <= found


class TestWhatDoesNot:
    def test_a_configuration_field_with_the_same_name(self):
        assert imports_in("tool_shortlist: ToolShortlistConfig = Field()") == set()

    def test_a_function_named_after_it(self):
        assert (
            imports_in("def _build_tool_shortlist(resolved):\n    return None") == set()
        )

    def test_a_mention_in_a_comment(self):
        assert imports_in("# see tool_shortlist for the other half") == set()

    def test_a_mention_in_a_log_line(self):
        assert imports_in('logger.info("tool_shortlist is on")') == set()

    def test_a_string_that_happens_to_contain_it(self):
        assert imports_in('path = "src/security/taint.py"') == set()


class TestItSurvivesTheTree:
    def test_a_file_that_will_not_parse_is_not_a_crash(self):
        assert imports_in("def (((") == set()

    def test_an_empty_file_references_nothing(self):
        assert imports_in("") == set()


class TestThingsTheRuntimeLoadsByName:
    """Not every entry point is imported by something here."""

    @staticmethod
    def _exempt():
        from test_unreachable_modules import LOADED_BY_NAME

        return LOADED_BY_NAME

    def test_the_command_line_entry_point_is_exempt(self):
        assert "cli/main.py" in self._exempt()

    def test_the_server_app_is_exempt(self):
        assert "aegra/http_app.py" in self._exempt()

    def test_the_exemptions_are_paths_not_bare_filenames(self):
        assert all("/" in name for name in self._exempt())

    def test_nothing_exempt_is_reported(self):
        from test_unreachable_modules import unreachable

        reported = {str(p) for p in unreachable()}
        assert not (reported & self._exempt())
