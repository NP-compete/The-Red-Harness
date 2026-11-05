"""The declared shape of a space says everything the store does."""

from __future__ import annotations

from agent.aegra.space_routes import SpaceOut
from agent.src.spaces.store import Space


def _a_space() -> Space:
    return Space(
        space_id="s-1",
        name="a room",
        group_cn="a-group",
        created_by="somebody",
        created_at="2026-10-31T00:00:00+00:00",
        always_on=True,
    )


class TestNothingIsFilteredOut:
    def test_the_model_names_every_field_the_store_returns(self):
        sent = set(_a_space().as_dict())
        declared = set(SpaceOut.model_fields)
        missing = sent - declared
        assert not missing, (
            f"SpaceOut does not declare {sorted(missing)}, and `GET /spaces` uses "
            "response_model= — so those fields are deleted from the payload at "
            "runtime and no client can see them."
        )

    def test_always_on_survives_the_model(self):
        room = _a_space().as_dict()
        assert SpaceOut.model_validate(room).always_on is True

    def test_a_room_round_trips(self):
        room = _a_space().as_dict()
        assert SpaceOut.model_validate(room).model_dump(mode="json") == room
