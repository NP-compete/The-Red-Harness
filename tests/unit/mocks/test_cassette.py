"""Replaying a recorded conversation (E27-T3)."""

from __future__ import annotations

import json

import pytest

from tests.fixtures.replay import CassetteMiss, answer_from, key_for, load, record


class TestTheKey:
    def test_the_same_conversation_keys_the_same(self):
        one = [{"role": "user", "content": "hello"}]
        assert key_for(one) == key_for([dict(one[0])])

    def test_a_different_conversation_does_not(self):
        assert key_for([{"role": "user", "content": "a"}]) != key_for(
            [{"role": "user", "content": "b"}]
        )

    def test_a_knob_the_provider_added_does_not_change_it(self):
        plain = [{"role": "user", "content": "hello"}]
        richer = [{"role": "user", "content": "hello", "reasoning_details": {"x": 1}}]
        assert key_for(plain) == key_for(richer)

    def test_content_blocks_read_as_their_text(self):
        blocks = [{"role": "user", "content": [{"type": "text", "text": "hello"}]}]
        assert key_for(blocks) == key_for([{"role": "user", "content": "hello"}])


class TestReplay:
    def test_a_recorded_answer_comes_back(self, tmp_path):
        where = tmp_path / "c.json"
        messages = [{"role": "user", "content": "what is the policy?"}]
        record(where, messages, {"content": "eight weeks"})
        assert answer_from(load(where), messages)["content"] == "eight weeks"

    def test_a_tool_call_survives_the_round_trip(self, tmp_path):
        where = tmp_path / "c.json"
        messages = [{"role": "user", "content": "read it"}]
        call = {
            "id": "c1",
            "type": "function",
            "function": {"name": "read_file", "arguments": "{}"},
        }
        record(where, messages, {"content": "", "tool_call": call})
        assert answer_from(load(where), messages)["tool_call"] == call

    def test_recording_a_second_exchange_keeps_the_first(self, tmp_path):
        where = tmp_path / "c.json"
        record(where, [{"role": "user", "content": "a"}], {"content": "1"})
        record(where, [{"role": "user", "content": "b"}], {"content": "2"})
        assert len(load(where)) == 2

    def test_the_file_is_readable_as_a_diff(self, tmp_path):
        where = tmp_path / "c.json"
        record(where, [{"role": "user", "content": "a"}], {"content": "1"})
        assert where.read_text().count("\n") > 3
        assert json.loads(where.read_text())


class TestAMissIsAFailure:
    def test_it_raises_rather_than_inventing(self, tmp_path):
        where = tmp_path / "c.json"
        record(where, [{"role": "user", "content": "a"}], {"content": "1"})
        with pytest.raises(CassetteMiss):
            answer_from(load(where), [{"role": "user", "content": "never recorded"}])

    def test_the_miss_names_the_key_and_the_way_out(self, tmp_path):
        where = tmp_path / "c.json"
        record(where, [{"role": "user", "content": "a"}], {"content": "1"})
        messages = [{"role": "user", "content": "never recorded"}]
        with pytest.raises(CassetteMiss) as missing:
            answer_from(load(where), messages)
        said = str(missing.value)
        assert key_for(messages) in said
        assert "cassette-record" in said

    def test_an_absent_cassette_is_not_an_empty_one(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load(tmp_path / "nothing.json")


class TestRecordingIsCosted:
    def test_a_mock_is_refused(self):
        from scripts.dev.record_cassette import main

        assert (
            main(["--name", "x", "--prompts", "/etc/hosts", "--model", "mock-model"])
            == 2
        )

    def test_so_is_naming_no_model_at_all(self):
        from scripts.dev.record_cassette import main

        assert main(["--name", "x", "--prompts", "/etc/hosts", "--model", ""]) == 2
