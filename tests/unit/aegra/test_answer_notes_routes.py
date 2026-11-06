"""The notes an answer carries about how far it can be trusted."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from agent.aegra.answer_notes_routes import router


@pytest.fixture
def client() -> AsyncClient:
    app = FastAPI()
    app.include_router(router)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def body(**kwargs) -> dict:
    payload = {
        "answer": "The travel limit is 500 euros.",
        "sources": [
            {"id": "handbook", "text": "The travel limit is 500 euros."},
            {"id": "policy", "text": "Travel is capped at 500 euros per trip."},
        ],
        "coverage": 1.0,
        "claims_supported": 1.0,
        "sources_disagree": False,
        "oldest_source_days": 10,
        "freshness_matters": False,
        "built_on_untrusted": False,
        "withheld": 0,
        "requestable": [],
    }
    payload.update(kwargs)
    return payload


@pytest.mark.asyncio
async def test_a_well_supported_answer_is_stated_plainly(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body())
    assert got.json()["stance"] == "plain"


@pytest.mark.asyncio
async def test_a_thin_answer_is_hedged(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body(coverage=0.4))
    assert got.json()["stance"] == "hedged"


@pytest.mark.asyncio
async def test_a_hedged_answer_says_what_is_shaky(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body(coverage=0.4))
    assert got.json()["concerns"]


@pytest.mark.asyncio
async def test_an_answer_with_nothing_behind_it_is_declined(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body(sources=[]))
    assert got.json()["stance"] == "decline"


@pytest.mark.asyncio
async def test_a_figure_that_appears_nowhere_is_reported(client: AsyncClient):
    async with client as c:
        got = await c.post(
            "/answers/notes", json=body(answer="The limit is 750 euros.")
        )
    assert got.json()["figures"]["unsupported"] == ["750"]


@pytest.mark.asyncio
async def test_a_figure_that_checks_out_is_not_reported(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body())
    assert got.json()["figures"]["unsupported"] == []


@pytest.mark.asyncio
async def test_how_many_figures_were_checked_is_reported(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body())
    assert got.json()["figures"]["checked"] == 1


@pytest.mark.asyncio
async def test_results_held_back_are_counted(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body(withheld=2))
    assert got.json()["access"]["withheld"] == 2


@pytest.mark.asyncio
async def test_documents_the_asker_may_ask_for_are_named(client: AsyncClient):
    async with client as c:
        got = await c.post(
            "/answers/notes", json=body(withheld=1, requestable=["handbook"])
        )
    assert got.json()["access"]["requestable"] == ["handbook"]


@pytest.mark.asyncio
async def test_an_answer_held_back_entirely_says_so(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body(sources=[], withheld=3))
    assert got.json()["access"]["nothing_left"] is True


@pytest.mark.asyncio
async def test_an_answer_with_no_figures_checks_none(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body(answer="The limit is generous."))
    assert got.json()["figures"]["checked"] == 0


@pytest.mark.asyncio
async def test_an_empty_answer_is_refused(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body(answer="   "))
    assert got.status_code == 422


@pytest.mark.asyncio
async def test_a_coverage_outside_its_range_is_refused(client: AsyncClient):
    async with client as c:
        got = await c.post("/answers/notes", json=body(coverage=1.5))
    assert got.status_code == 422
