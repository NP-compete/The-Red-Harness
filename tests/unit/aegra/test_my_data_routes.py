"""Taking a copy of what is held, and asking for it to go."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from agent.aegra.http_app import app

    return TestClient(app)


def _held():
    return {
        "documents": [
            {"id": "user:1", "owner": "johnwick", "title": "Spending limits"}
        ],
        "artifacts": [{"id": "tally", "owner": "johnwick", "value": "3"}],
    }


def _asking(client, path, *, method="get", held=None):
    def _collect(subject):
        return held if held is not None else _held()

    with (
        patch("agent.aegra.my_data_routes._who", return_value="johnwick"),
        patch("agent.aegra.my_data_routes._held_about", side_effect=_collect),
    ):
        return getattr(client, method)(path)


class TestTakingACopy:
    def test_it_answers(self, client):
        assert _asking(client, "/me/export").status_code == 200

    def test_it_says_who_it_is_for(self, client):
        assert _asking(client, "/me/export").json()["subject"] == "johnwick"

    def test_it_carries_the_documents(self, client):
        found = _asking(client, "/me/export").json()
        assert found["sections"]["documents"]

    def test_it_carries_the_artifacts(self, client):
        found = _asking(client, "/me/export").json()
        assert found["sections"]["artifacts"]

    def test_it_counts_each_section(self, client):
        assert _asking(client, "/me/export").json()["counts"]["documents"] == 1

    def test_it_says_when_it_was_made(self, client):
        assert _asking(client, "/me/export").json()["made_at"]

    def test_a_store_that_was_not_collected_is_named(self):
        from agent.aegra.my_data_routes import _missing_from

        found = _missing_from({"documents": [{"id": "1"}]})
        assert "memory" in found

    def test_a_store_that_was_collected_is_not_named(self):
        from agent.aegra.my_data_routes import _missing_from

        assert "documents" not in _missing_from({"documents": [{"id": "1"}]})

    def test_an_empty_section_counts_as_collected(self):
        from agent.aegra.my_data_routes import _missing_from

        assert "artifacts" not in _missing_from({"artifacts": []})

    def test_the_export_says_it_is_incomplete_when_something_is_missing(self, client):
        found = _asking(client, "/me/export").json()
        assert found["complete"] is False

    def test_the_export_says_which_one(self, client):
        found = _asking(client, "/me/export").json()
        assert "memory" in found["withheld"]

    def test_it_says_why_rather_than_only_that(self, client):
        found = _asking(client, "/me/export").json()
        assert found["withheld"]["memory"].strip()

    def test_a_credential_never_travels(self, client):
        found = _asking(
            client,
            "/me/export",
            held={"sessions": [{"id": "s1", "owner": "johnwick", "token": "secret"}]},
        ).json()
        assert "secret" not in str(found)


class TestSeeingWhatWouldGo:
    def test_it_answers(self, client):
        assert _asking(client, "/me/deletion-preview").status_code == 200

    def test_it_lists_what_would_be_removed(self, client):
        found = _asking(client, "/me/deletion-preview").json()
        assert "user:1" in found["delete"]["documents"]

    def test_it_lists_what_would_survive(self, client):
        found = _asking(
            client,
            "/me/deletion-preview",
            held={
                "documents": [
                    {"id": "team:1", "owner": "johnwick", "scope": "team"},
                ]
            },
        ).json()
        assert "team:1" in found["kept"]["documents"]

    def test_it_says_the_audit_trail_stays(self, client):
        found = _asking(
            client,
            "/me/deletion-preview",
            held={"audit": [{"id": "a1", "owner": "johnwick"}]},
        ).json()
        assert found["notes"]

    def test_nothing_is_removed_by_looking(self, client):
        removed = []

        with (
            patch("agent.aegra.my_data_routes._who", return_value="johnwick"),
            patch("agent.aegra.my_data_routes._held_about", return_value=_held()),
            patch(
                "agent.aegra.my_data_routes._remove",
                side_effect=lambda *a, **k: removed.append(a),
            ),
        ):
            client.get("/me/deletion-preview")

        assert removed == []


class TestAskingForItToGo:
    @staticmethod
    def _deleting(client, held=None):
        removed = []

        def _remove(subject, section, ids):
            removed.extend(ids)

        with (
            patch("agent.aegra.my_data_routes._who", return_value="johnwick"),
            patch(
                "agent.aegra.my_data_routes._held_about",
                return_value=held if held is not None else _held(),
            ),
            patch("agent.aegra.my_data_routes._remove", side_effect=_remove),
        ):
            return client.delete("/me/data"), removed

    def test_it_answers(self, client):
        found, _removed = self._deleting(client)
        assert found.status_code == 200

    def test_it_removes_what_it_said_it_would(self, client):
        _found, removed = self._deleting(client)
        assert "user:1" in removed

    def test_it_reports_what_went(self, client):
        found, _removed = self._deleting(client)
        assert found.json()["counts"]["documents"] == 1

    def test_it_does_not_remove_shared_content(self, client):
        _found, removed = self._deleting(
            client,
            held={
                "documents": [{"id": "team:1", "owner": "johnwick", "scope": "team"}]
            },
        )
        assert removed == []

    def test_a_store_that_will_not_delete_is_reported_not_swallowed(self, client):
        def _remove(subject, section, ids):
            raise RuntimeError("store is down")

        with (
            patch("agent.aegra.my_data_routes._who", return_value="johnwick"),
            patch("agent.aegra.my_data_routes._held_about", return_value=_held()),
            patch("agent.aegra.my_data_routes._remove", side_effect=_remove),
        ):
            found = client.delete("/me/data")

        assert found.json()["failed"]

    def test_one_store_failing_does_not_stop_the_others(self, client):
        removed = []

        def _remove(subject, section, ids):
            if section == "documents":
                raise RuntimeError("store is down")
            removed.extend(ids)

        with (
            patch("agent.aegra.my_data_routes._who", return_value="johnwick"),
            patch("agent.aegra.my_data_routes._held_about", return_value=_held()),
            patch("agent.aegra.my_data_routes._remove", side_effect=_remove),
        ):
            client.delete("/me/data")

        assert "tally" in removed


class TestTheGapIsSaidBeforeTheAction:
    """A label that overstates what a button does."""

    def test_the_preview_says_what_is_not_covered(self, client):
        found = _asking(client, "/me/deletion-preview").json()
        assert "memory" in found["not_included"]

    def test_it_says_why(self, client):
        found = _asking(client, "/me/deletion-preview").json()
        assert found["not_included"]["memory"].strip()

    def test_the_result_says_it_too(self, client):
        with (
            patch("agent.aegra.my_data_routes._who", return_value="johnwick"),
            patch("agent.aegra.my_data_routes._held_about", return_value=_held()),
            patch("agent.aegra.my_data_routes._remove", return_value=None),
        ):
            found = client.delete("/me/data")

        assert "memory" in found.json()["not_included"]
