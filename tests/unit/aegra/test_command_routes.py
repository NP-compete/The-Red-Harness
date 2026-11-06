"""The commands a reader can type, as the composer sees them."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from agent.aegra.command_routes import router


@pytest.fixture
def client() -> AsyncClient:
    app = FastAPI()
    app.include_router(router)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_the_commands_are_listed(client: AsyncClient):
    async with client as c:
        got = await c.get("/commands")
    assert got.json()["commands"]


@pytest.mark.asyncio
async def test_each_command_carries_its_name(client: AsyncClient):
    async with client as c:
        got = await c.get("/commands")
    assert all(command["name"] for command in got.json()["commands"])


@pytest.mark.asyncio
async def test_each_command_explains_itself(client: AsyncClient):
    async with client as c:
        got = await c.get("/commands")
    assert all(command["help"] for command in got.json()["commands"])


@pytest.mark.asyncio
async def test_the_prompt_behind_a_command_is_not_published(client: AsyncClient):
    async with client as c:
        got = await c.get("/commands")
    assert all("prompt" not in command for command in got.json()["commands"])


@pytest.mark.asyncio
async def test_the_list_is_in_a_settled_order(client: AsyncClient):
    async with client as c:
        got = await c.get("/commands")
    names = [command["name"] for command in got.json()["commands"]]
    assert names == sorted(names)
