"""One suite every channel adapter passes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from agent.src.channels.adapters import AdapterError, InboundMessage, parse

from .samples import EVERY_ADAPTER, Sample

pytestmark = pytest.mark.integration

ADAPTERS = pytest.mark.parametrize("sample", EVERY_ADAPTER, ids=lambda s: s.channel)


@ADAPTERS
class TestItProducesSomethingTheAgentCanRun:
    def test_a_valid_payload_parses(self, sample: Sample):
        assert isinstance(parse(sample.channel, sample.valid), InboundMessage)

    def test_the_sender_is_named(self, sample: Sample):
        assert parse(sample.channel, sample.valid).sender

    def test_the_text_survives(self, sample: Sample):
        assert parse(sample.channel, sample.valid).text

    def test_the_text_is_trimmed(self, sample: Sample):
        said = parse(sample.channel, sample.valid).text
        assert said == said.strip()


@ADAPTERS
class TestThreading:
    def test_a_conversation_has_a_key(self, sample: Sample):
        assert parse(sample.channel, sample.valid).conversation

    def test_the_same_conversation_maps_to_the_same_key(self, sample: Sample):
        first = parse(sample.channel, sample.valid)
        again = parse(sample.channel, sample.same_conversation)
        assert first.conversation == again.conversation

    def test_a_different_conversation_does_not_collide(self, sample: Sample):
        first = parse(sample.channel, sample.valid)
        other = parse(sample.channel, sample.other_conversation)
        assert first.conversation != other.conversation

    def test_the_key_names_its_channel(self, sample: Sample):
        assert parse(sample.channel, sample.valid).conversation.startswith(
            f"{sample.channel}:"
        )

    def test_the_same_payload_twice_gives_the_same_key(self, sample: Sample):
        once = parse(sample.channel, sample.valid)
        twice = parse(sample.channel, sample.valid)
        assert once.conversation == twice.conversation


@ADAPTERS
class TestItDoesNotAnswerItself:
    def test_an_echo_of_our_own_message_is_ignored(self, sample: Sample):
        if sample.echo is None:
            pytest.skip(f"{sample.channel} cannot echo the agent back to itself")
        assert parse(sample.channel, sample.echo) is None


@ADAPTERS
class TestFailureSemantics:
    def test_a_malformed_payload_raises(self, sample: Sample):
        for payload in sample.malformed:
            with pytest.raises(AdapterError):
                parse(sample.channel, payload)

    def test_it_never_half_parses(self, sample: Sample):
        for payload in sample.malformed:
            try:
                found = parse(sample.channel, payload)
            except AdapterError:
                continue
            assert found is None or (found.sender and found.text)

    def test_something_deliberately_ignored_is_not_an_error(self, sample: Sample):
        for payload in sample.ignored:
            assert parse(sample.channel, payload) is None


class TestTheSuiteCoversEveryAdapter:
    """A parser with no sample is a parser nothing here checks."""

    def test_every_registered_parser_has_a_sample(self):
        from agent.src.channels.adapters import PARSERS

        covered = {sample.channel for sample in EVERY_ADAPTER}
        assert set(PARSERS) == covered


class TestConversationKeysCannotBeForgedAcrossChannels:
    """One channel must not be able to address another's thread."""

    def test_a_caller_cannot_claim_another_channels_conversation(self):
        stolen = parse(
            "webhook",
            {
                "sender": "mallory",
                "text": "hello",
                "conversation": "slack:C1:1700000000.1",
            },
        )
        assert not stolen.conversation.startswith("slack:")


@ADAPTERS
class TestIdentityMapping:
    """Who sent it, decided the same way for every channel."""

    def _inbound(self, sample: Sample, *, verified: bool = True):
        from agent.src.security.channel_identity import Inbound

        parsed = parse(sample.channel, sample.valid)
        assert parsed is not None
        return Inbound(
            channel=sample.channel, external_id=parsed.sender, verified=verified
        )

    def test_a_known_sender_maps_to_their_account(self, sample: Sample):
        from agent.src.security.channel_identity import resolve_sender

        message = self._inbound(sample)
        directory = {f"{message.channel}:{message.external_id}": "person-1"}
        found = resolve_sender(message, directory=directory)
        assert found is not None and found.subject == "person-1"

    def test_an_unknown_sender_maps_to_nobody(self, sample: Sample):
        from agent.src.security.channel_identity import resolve_sender

        assert resolve_sender(self._inbound(sample), directory={}) is None

    def test_an_unverified_message_maps_to_nobody(self, sample: Sample):
        from agent.src.security.channel_identity import resolve_sender

        message = self._inbound(sample, verified=False)
        directory = {f"{message.channel}:{message.external_id}": "person-1"}
        assert resolve_sender(message, directory=directory) is None

    def test_one_channels_id_does_not_unlock_another(self, sample: Sample):
        from agent.src.security.channel_identity import Inbound, resolve_sender

        message = self._inbound(sample)
        directory = {f"other:{message.external_id}": "person-1"}
        elsewhere = Inbound(
            channel=sample.channel, external_id=message.external_id, verified=True
        )
        assert resolve_sender(elsewhere, directory=directory) is None


@ADAPTERS
class TestNoDoubleDelivery:
    """One answer reaches the channel once."""

    @staticmethod
    def _payload(sample: Sample) -> dict:
        """The payload this adapter can be replied to."""
        found = sample.deliverable or sample.valid
        parsed = parse(sample.channel, found)
        assert parsed is not None
        if sample.channel != "slack" and not parsed.reply_to:
            pytest.skip(f"{sample.channel} has no payload with somewhere to reply")
        return found

    async def _deliver_twice(self, sample: Sample, monkeypatch):
        from agent.src.channels import dispatch

        sent: list[str] = []

        async def _record(reply, message):
            sent.append(reply)
            # The real `_deliver_*` returns whether it arrived, and
            # `deliver` forgets the delivery when it did not so a
            # retry can happen. A stub returning None says "did not
            # arrive", so the dedupe correctly let the retry through
            # and the test read that as double delivery.
            return True

        monkeypatch.setattr(dispatch, "_deliver_slack", _record)
        monkeypatch.setattr(dispatch, "_deliver_webhook", _record)

        message = parse(sample.channel, self._payload(sample))
        assert message is not None
        channel = SimpleNamespace(type=sample.channel)
        await dispatch.deliver("the answer", message, channel)
        again = parse(sample.channel, self._payload(sample))
        await dispatch.deliver("the answer", again, channel)
        return sent

    @pytest.mark.asyncio
    async def test_a_retry_of_the_same_event_delivers_once(
        self, sample: Sample, monkeypatch
    ):
        assert await self._deliver_twice(sample, monkeypatch) == ["the answer"]

    @pytest.mark.asyncio
    async def test_a_different_answer_is_not_suppressed(
        self, sample: Sample, monkeypatch
    ):
        from agent.src.channels import dispatch

        sent: list[str] = []

        async def _record(reply, message):
            sent.append(reply)
            # The real `_deliver_*` returns whether it arrived, and
            # `deliver` forgets the delivery when it did not so a
            # retry can happen. A stub returning None says "did not
            # arrive", so the dedupe correctly let the retry through
            # and the test read that as double delivery.
            return True

        monkeypatch.setattr(dispatch, "_deliver_slack", _record)
        monkeypatch.setattr(dispatch, "_deliver_webhook", _record)

        message = parse(sample.channel, self._payload(sample))
        channel = SimpleNamespace(type=sample.channel)
        await dispatch.deliver("first", message, channel)
        await dispatch.deliver("second", message, channel)
        assert sent == ["first", "second"]

    @pytest.mark.asyncio
    async def test_a_failed_delivery_may_be_retried(self, sample: Sample, monkeypatch):
        from agent.src.channels import dispatch

        sent: list[str] = []

        async def _broken(reply, message):
            raise RuntimeError("channel down")

        async def _record(reply, message):
            sent.append(reply)
            # The real `_deliver_*` returns whether it arrived, and
            # `deliver` forgets the delivery when it did not so a
            # retry can happen. A stub returning None says "did not
            # arrive", so the dedupe correctly let the retry through
            # and the test read that as double delivery.
            return True

        message = parse(sample.channel, self._payload(sample))
        channel = SimpleNamespace(type=sample.channel)

        monkeypatch.setattr(dispatch, "_deliver_slack", _broken)
        monkeypatch.setattr(dispatch, "_deliver_webhook", _broken)
        with pytest.raises(RuntimeError):
            await dispatch.deliver("the answer", message, channel)

        monkeypatch.setattr(dispatch, "_deliver_slack", _record)
        monkeypatch.setattr(dispatch, "_deliver_webhook", _record)
        await dispatch.deliver("the answer", message, channel)
        assert sent == ["the answer"]

    @pytest.mark.asyncio
    async def test_the_record_does_not_grow_without_bound(
        self, sample: Sample, monkeypatch
    ):
        from agent.src.channels import dispatch

        async def _record(reply, message):
            return None

        monkeypatch.setattr(dispatch, "_deliver_slack", _record)
        monkeypatch.setattr(dispatch, "_deliver_webhook", _record)

        message = parse(sample.channel, self._payload(sample))
        channel = SimpleNamespace(type=sample.channel)
        for i in range(2000):
            await dispatch.deliver(f"answer {i}", message, channel)
        assert len(dispatch._DELIVERED) <= 1024
