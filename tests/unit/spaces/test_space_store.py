"""E33-T1. What a space is, and what it refuses to be."""

from __future__ import annotations

import pytest

from agent.src.spaces.errors import SpaceRefused
from agent.src.spaces.store import MAX_NAME, Space, validate


class TestValidate:
    def test_a_name_and_a_group_are_enough(self):
        assert validate(" Billing ", " cn=billing ") == ("Billing", "cn=billing")

    def test_a_space_needs_a_name(self):
        with pytest.raises(SpaceRefused, match="needs a name"):
            validate("   ", "cn=billing")

    def test_a_space_needs_a_group(self):
        """Not a cosmetic requirement."""
        with pytest.raises(SpaceRefused, match="identity provider"):
            validate("Billing", "")

    def test_an_overlong_name_is_refused(self):
        with pytest.raises(SpaceRefused, match=str(MAX_NAME)):
            validate("x" * (MAX_NAME + 1), "cn=billing")


class TestSpace:
    def test_the_payload_carries_the_group_not_a_member_list(self):
        """A reader should see *why* they are in a room."""
        payload = Space("s1", "Billing", "cn=billing", "ada").as_dict()
        assert payload["group_cn"] == "cn=billing"
        assert "members" not in payload
        assert "member_list" not in payload

    def test_always_on_is_off_by_default(self):
        """A room where the agent answers everything is noise."""
        assert Space("s1", "Billing", "cn=billing", "ada").always_on is False
