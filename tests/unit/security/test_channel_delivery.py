"""Sending an answer back out, without letting delivery break the run."""

from __future__ import annotations

from agent.src.security.channel_delivery import deliver


class Channel:
    def __init__(self, name="slack", fail=False, limit=4000):
        self.name = name
        self.limit = limit
        self.sent: list[str] = []
        self._fail = fail

    def send(self, text: str) -> None:
        if self._fail:
            raise RuntimeError("channel unavailable")
        self.sent.append(text)


def test_an_answer_is_sent():
    channel = Channel()
    deliver("the answer", channel=channel)
    assert channel.sent == ["the answer"]


def test_delivery_reports_success():
    assert deliver("x", channel=Channel()).sent is True


def test_a_failing_channel_does_not_raise():
    assert deliver("x", channel=Channel(fail=True)).sent is False


def test_a_failure_says_which_channel_and_why():
    result = deliver("x", channel=Channel(fail=True))
    assert result.channel == "slack"
    assert "unavailable" in result.error


def test_a_long_answer_is_split_rather_than_truncated():
    channel = Channel(limit=10)
    deliver("abcdefghijklmnopqrst", channel=channel)
    assert "".join(channel.sent) == "abcdefghijklmnopqrst"


def test_each_part_fits_the_channel():
    channel = Channel(limit=10)
    deliver("abcdefghijklmnopqrst", channel=channel)
    assert all(len(part) <= 10 for part in channel.sent)


def test_the_number_of_parts_is_reported():
    assert deliver("abcdefghijklmnopqrst", channel=Channel(limit=10)).parts == 2


def test_a_short_answer_is_one_part():
    assert deliver("short", channel=Channel(limit=4000)).parts == 1


def test_an_empty_answer_is_not_sent_at_all():
    channel = Channel()
    result = deliver("   ", channel=channel)
    assert channel.sent == []
    assert result.sent is False


def test_a_partial_failure_is_reported_as_a_failure():
    class HalfBroken(Channel):
        def send(self, text: str) -> None:
            if len(self.sent) >= 1:
                raise RuntimeError("rate limited")
            self.sent.append(text)

    result = deliver("abcdefghijklmnopqrst", channel=HalfBroken(limit=10))
    assert result.sent is False
    assert result.parts == 1
