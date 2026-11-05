"""A setting written twice is a setting silently discarded."""

from __future__ import annotations

from agent.src.agent.config.duplicate_keys import duplicate_keys


class TestNothingWrong:
    def test_an_ordinary_file_has_none(self):
        assert duplicate_keys("a: 1\nb: 2\n") == []

    def test_an_empty_file_has_none(self):
        assert duplicate_keys("") == []

    def test_the_same_name_under_different_parents_is_not_a_duplicate(self):
        assert duplicate_keys("one:\n  name: a\ntwo:\n  name: b\n") == []

    def test_a_list_of_similar_entries_is_not_a_duplicate(self):
        text = "servers:\n  - name: a\n    url: x\n  - name: b\n    url: y\n"
        assert duplicate_keys(text) == []


class TestASettingWrittenTwice:
    def test_a_repeated_top_level_key_is_found(self):
        assert duplicate_keys("a: 1\nb: 2\na: 3\n")

    def test_it_says_which_key(self):
        assert "a" in duplicate_keys("a: 1\nb: 2\na: 3\n")[0]

    def test_a_repeated_nested_key_is_found(self):
        found = duplicate_keys("middleware:\n  extra: []\n  other: 1\n  extra: [x]\n")
        assert len(found) == 1

    def test_a_nested_key_is_named_with_its_parent(self):
        found = duplicate_keys("middleware:\n  extra: []\n  other: 1\n  extra: [x]\n")
        assert "middleware.extra" in found[0]

    def test_it_says_where_to_look(self):
        found = duplicate_keys("middleware:\n  extra: []\n  other: 1\n  extra: [x]\n")
        assert "line 4" in found[0]

    def test_every_repeat_is_reported_not_only_the_first(self):
        found = duplicate_keys("a: 1\na: 2\nb: 3\nb: 4\n")
        assert len(found) == 2

    def test_a_key_written_three_times_is_reported_twice(self):
        assert len(duplicate_keys("a: 1\na: 2\na: 3\n")) == 2

    def test_a_duplicate_inside_a_list_entry_is_found(self):
        text = "servers:\n  - name: a\n    url: x\n    name: b\n"
        assert duplicate_keys(text)


class TestItNeverGetsInTheWay:
    def test_a_file_that_will_not_parse_reports_nothing_rather_than_raising(self):
        assert duplicate_keys("a: [1, 2\nb: }{\n") == []

    def test_a_file_that_is_only_a_comment_reports_nothing(self):
        assert duplicate_keys("# nothing here\n") == []


class TestTheLoaderSaysSoAtStartup:
    """`make validate-config` catches this, but only for somebody who"""

    def _load(self, tmp_path, text, caplog, monkeypatch):
        import logging

        from agent.src.agent.config import agent_config

        written = tmp_path / "agent.yaml"
        written.write_text(text)
        monkeypatch.setattr(agent_config, "_resolve", lambda *_: written)

        with caplog.at_level(logging.WARNING):
            loaded = agent_config._load_agent_yaml()
        return loaded, caplog.text

    def test_a_duplicate_is_called_out(self, tmp_path, caplog, monkeypatch):
        _, said = self._load(
            tmp_path, "middleware:\n  a: 1\n  a: 2\n", caplog, monkeypatch
        )
        assert "more than once" in said

    def test_the_warning_names_the_key(self, tmp_path, caplog, monkeypatch):
        _, said = self._load(
            tmp_path, "middleware:\n  a: 1\n  a: 2\n", caplog, monkeypatch
        )
        assert "middleware.a" in said

    def test_an_ordinary_file_is_not_complained_about(
        self, tmp_path, caplog, monkeypatch
    ):
        _, said = self._load(
            tmp_path, "middleware:\n  a: 1\n  b: 2\n", caplog, monkeypatch
        )
        assert "more than once" not in said

    def test_the_config_still_loads(self, tmp_path, caplog, monkeypatch):
        loaded, _ = self._load(
            tmp_path, "middleware:\n  a: 1\n  a: 2\n", caplog, monkeypatch
        )
        assert loaded["middleware"]["a"] == 2
