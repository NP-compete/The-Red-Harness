"""E41-T3. Who `@` may address in a room."""

from __future__ import annotations

from agent.src.spaces import people


class TestReadingAHandle:
    def test_a_distinguished_name_is_a_person(self):
        assert people._handle_of("uid=ada,ou=users,dc=example,dc=com") == "ada"

    def test_a_bare_uid_is_already_a_person(self):
        assert people._handle_of("ada") == "ada"

    def test_nothing_is_nobody(self):
        assert people._handle_of("   ") == ""
        assert people._handle_of("cn=,ou=users") == ""


class TestAskingTheDirectory:
    def test_no_group_asks_nothing(self):
        assert people.members_of_group_sync("") == ()

    def test_an_unreachable_directory_is_empty_rather_than_an_error(self, monkeypatch):
        """A composer must not fall over because LDAP is down."""
        monkeypatch.setattr(
            "agent.src.ldap.service._ensure_bound", lambda: None, raising=False
        )
        assert people.members_of_group_sync("cn=billing") == ()

    def test_a_room_is_not_a_phone_book(self):
        assert people.MAX_PEOPLE <= 100
