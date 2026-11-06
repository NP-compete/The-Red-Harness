"""When a long conversation gets summarised, and how much survives."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.src.agent.config.middleware import CompactionConfig


class TestLeftAlone:
    def test_a_deployment_that_says_nothing_changes_nothing(self):
        assert CompactionConfig().configured is False

    def test_saying_nothing_leaves_no_trigger_to_apply(self):
        assert CompactionConfig().trigger() is None

    def test_saying_nothing_leaves_no_tail_to_keep(self):
        assert CompactionConfig().keep() is None


class TestWhenItFires:
    def test_a_fraction_of_the_window_is_a_trigger(self):
        assert CompactionConfig(trigger_fraction=0.7).trigger() == ("fraction", 0.7)

    def test_naming_a_fraction_is_enough_to_count_as_configured(self):
        assert CompactionConfig(trigger_fraction=0.7).configured is True

    def test_a_fraction_at_the_very_top_of_the_window_is_allowed(self):
        assert CompactionConfig(trigger_fraction=1.0).trigger() == ("fraction", 1.0)

    def test_a_fraction_past_the_window_is_refused(self):
        with pytest.raises(ValidationError):
            CompactionConfig(trigger_fraction=1.2)

    def test_a_fraction_of_nothing_is_refused(self):
        with pytest.raises(ValidationError):
            CompactionConfig(trigger_fraction=0)

    def test_a_negative_fraction_is_refused(self):
        with pytest.raises(ValidationError):
            CompactionConfig(trigger_fraction=-0.5)


class TestWhatSurvives:
    def test_a_number_of_recent_messages_is_a_tail(self):
        assert CompactionConfig(keep_messages=30).keep() == ("messages", 30)

    def test_naming_a_tail_is_enough_to_count_as_configured(self):
        assert CompactionConfig(keep_messages=30).configured is True

    def test_keeping_nothing_is_refused(self):
        with pytest.raises(ValidationError):
            CompactionConfig(keep_messages=0)

    def test_keeping_a_negative_number_is_refused(self):
        with pytest.raises(ValidationError):
            CompactionConfig(keep_messages=-1)


class TestBothTogether:
    def test_each_is_read_independently_of_the_other(self):
        config = CompactionConfig(trigger_fraction=0.6, keep_messages=40)
        assert config.trigger() == ("fraction", 0.6)
        assert config.keep() == ("messages", 40)

    def test_a_tail_alone_leaves_the_trigger_as_it_was(self):
        assert CompactionConfig(keep_messages=40).trigger() is None

    def test_a_trigger_alone_leaves_the_tail_as_it_was(self):
        assert CompactionConfig(trigger_fraction=0.6).keep() is None
