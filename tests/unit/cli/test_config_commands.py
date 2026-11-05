"""E28. The configuration tree from a terminal."""

from __future__ import annotations

import pytest

from agent.cli.config import (
    ConfigFailed,
    ReadOnlyDeployment,
    list_files,
    set_file,
    show_file,
)


class _Transport:
    def __init__(self, answers: dict[str, tuple[int, object]]):
        self.answers = answers
        self.sent: list[tuple[str, str, object]] = []

    def get(self, path: str):
        self.sent.append(("GET", path, None))
        for key, answer in self.answers.items():
            if path.startswith(key):
                return answer
        return 404, {"message": "no such route"}

    def put(self, path: str, body=None):
        self.sent.append(("PUT", path, body))
        return self.answers.get(
            "PUT", (200, {"path": "p", "version": 1, "durable": False})
        )

    def post(self, path: str, body=None):
        self.sent.append(("POST", path, body))
        return 405, {"message": "Method Not Allowed"}


WRITABLE = {
    "/config/editing": (200, {"editable": True, "mode": "readwrite"}),
    "/config/file": (200, {"content": "old", "version": 4, "exists": True}),
    "/config/tree": (
        200,
        {"files": [{"path": "config/agent/PROMPT.md", "editable": True, "bytes": 10}]},
    ),
}


class TestReading:
    def test_the_list_includes_what_cannot_be_changed(self):
        """ "No such file" and "not editable from here" are"""
        rows = list_files(transport=_Transport(WRITABLE))
        assert rows[0].path == "config/agent/PROMPT.md"
        assert rows[0].editable is True

    def test_a_file_comes_back_with_its_version(self):
        found = show_file("config/agent/PROMPT.md", transport=_Transport(WRITABLE))
        assert (found.content, found.version) == ("old", 4)

    def test_a_path_the_agent_will_not_serve_is_refused(self):
        transport = _Transport(
            {"/config/file": (400, {"message": "not an editable path"})}
        )
        with pytest.raises(ConfigFailed, match="not an editable path"):
            show_file("/etc/passwd", transport=transport)


class TestWriting:
    def test_it_carries_the_version_it_read(self):
        """Two editors racing get a conflict naming both, rather"""
        transport = _Transport(WRITABLE)
        set_file("config/agent/PROMPT.md", "new", transport=transport)
        wrote = [one for one in transport.sent if one[0] == "PUT"][0]
        assert wrote[2]["base_version"] == 4

    def test_it_is_a_put_because_that_is_what_the_editor_sends(self):
        """Posting it answers 405 — a method mismatch reported as"""
        transport = _Transport(WRITABLE)
        set_file("config/agent/PROMPT.md", "new", transport=transport)
        assert any(one[0] == "PUT" for one in transport.sent)

    def test_force_sends_no_version_and_the_agent_logs_that(self):
        transport = _Transport(WRITABLE)
        set_file("config/agent/PROMPT.md", "new", transport=transport, force=True)
        wrote = [one for one in transport.sent if one[0] == "PUT"][0]
        assert wrote[2]["base_version"] is None

    def test_a_read_only_deployment_is_refused_before_anything_is_sent(self):
        """A blind write meets a 404 and reports "not found","""
        transport = _Transport(
            {"/config/editing": (200, {"editable": False, "mode": "readonly"})}
        )
        with pytest.raises(ReadOnlyDeployment, match="readonly"):
            set_file("config/agent/PROMPT.md", "new", transport=transport)
        assert not [one for one in transport.sent if one[0] == "PUT"]

    def test_a_stale_version_says_to_read_it_again(self):
        transport = _Transport(
            {**WRITABLE, "PUT": (409, {"message": "you have version 2"})}
        )
        with pytest.raises(ConfigFailed, match="Read it again"):
            set_file("config/agent/PROMPT.md", "new", transport=transport)

    def test_an_invalid_edit_carries_the_agents_own_reason(self):
        transport = _Transport(
            {**WRITABLE, "PUT": (422, {"message": "schema_version is 99"})}
        )
        with pytest.raises(ConfigFailed, match="schema_version is 99"):
            set_file("config/agent/PROMPT.md", "new", transport=transport)

    def test_an_older_agent_with_no_editing_route_is_still_attempted(self):
        """Refused by the write if it refuses, rather than by a"""
        transport = _Transport(
            {"/config/file": (200, {"content": "old", "version": 1})}
        )
        set_file("config/agent/PROMPT.md", "new", transport=transport)
        assert any(one[0] == "PUT" for one in transport.sent)

    def test_and_a_404_on_the_write_is_read_as_a_closed_door(self):
        transport = _Transport(
            {"/config/file": (200, {"content": "old", "version": 1}), "PUT": (404, {})}
        )
        with pytest.raises(ReadOnlyDeployment, match="no write route"):
            set_file("config/agent/PROMPT.md", "new", transport=transport)


SCHEMA_OK = (200, {"schema": {"current": 3, "oldest_supported": 2, "declared": 3}})


class TestTheSchemaIsCheckedFirst:
    """E28-T6: run against the version the server holds."""

    def _agent(self, declared):
        return _Transport(
            {
                "/admin/config": (
                    200,
                    {
                        "schema": {
                            "current": 3,
                            "oldest_supported": 2,
                            "declared": declared,
                        }
                    },
                ),
                "/config/drift": (200, {"paths": []}),
            }
        )

    def test_a_tree_from_the_future_is_refused_naming_both(self):
        from agent.cli.config import SchemaMismatch, diff

        with pytest.raises(SchemaMismatch) as refused:
            diff(transport=self._agent(9))
        assert "2 to 3" in str(refused.value) and "9" in str(refused.value)

    def test_so_is_one_too_old_to_read(self):
        from agent.cli.config import SchemaMismatch, diff

        with pytest.raises(SchemaMismatch):
            diff(transport=self._agent(1))

    def test_a_tree_that_declares_nothing_is_the_oldest_supported(self):
        from agent.cli.config import diff

        assert diff(transport=self._agent(None)) == ""

    def test_an_agent_that_does_not_publish_it_is_not_fatal(self):
        from agent.cli.config import diff

        transport = _Transport(
            {
                "/admin/config": (200, {}),
                "/config/drift": (200, {"paths": []}),
            }
        )
        assert diff(transport=transport) == ""


class TestTheDiff:
    def _drifted(self):
        return _Transport(
            {
                "/admin/config": SCHEMA_OK,
                "/config/drift": (
                    200,
                    {
                        "paths": [
                            {
                                "path": "config/agent/PROMPT.md",
                                "baseline": "one\ntwo\n",
                                "overlay": "one\ntwo\nthree\n",
                                "version": 4,
                                "author": "ada",
                            }
                        ]
                    },
                ),
            }
        )

    def test_it_reads_as_what_the_edit_would_do_to_the_tree(self):
        from agent.cli.config import diff

        found = diff(transport=self._drifted())
        assert "--- a/config/agent/PROMPT.md" in found
        assert "+three" in found

    def test_it_names_the_version_and_who_wrote_it(self):
        from agent.cli.config import diff

        found = diff(transport=self._drifted())
        assert "v4" in found and "ada" in found

    def test_an_untouched_deployment_diffs_to_nothing(self):
        from agent.cli.config import diff

        transport = _Transport(
            {
                "/admin/config": SCHEMA_OK,
                "/config/drift": (200, {"paths": []}),
            }
        )
        assert diff(transport=transport) == ""


class TestRender:
    def _tree(self, extra=None):
        answers = {
            "/admin/config": SCHEMA_OK,
            "/config/tree": (
                200,
                {
                    "files": [
                        {"path": "config/agent/PROMPT.md", "editable": True, "bytes": 3}
                    ]
                },
            ),
            "/config/file": (
                200,
                {"content": "live text", "version": 2, "exists": True},
            ),
        }
        answers.update(extra or {})
        return _Transport(answers)

    def test_it_writes_what_the_agent_reads_now(self, tmp_path):
        from agent.cli.config import render

        made = render(transport=self._tree(), out=tmp_path)
        assert made.written == ["config/agent/PROMPT.md"]
        assert (tmp_path / "config/agent/PROMPT.md").read_text() == "live text"

    def test_a_file_the_deployment_will_not_serve_is_counted_not_dropped(
        self, tmp_path
    ):
        from agent.cli.config import render

        made = render(
            transport=self._tree({"/config/file": (400, {"message": "not editable"})}),
            out=tmp_path,
        )
        assert made.written == [] and made.skipped == ["config/agent/PROMPT.md"]

    def test_a_path_that_would_escape_the_directory_is_refused(self, tmp_path):
        from agent.cli.config import ConfigFailed, render

        transport = self._tree(
            {
                "/config/tree": (
                    200,
                    {
                        "files": [
                            {"path": "../../escaped.md", "editable": True, "bytes": 1}
                        ]
                    },
                )
            }
        )
        with pytest.raises(ConfigFailed, match="outside"):
            render(transport=transport, out=tmp_path / "here")
