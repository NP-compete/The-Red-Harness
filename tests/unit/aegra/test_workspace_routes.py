"""The files an agent wrote for a person, which nothing could reach."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agent.aegra import workspace_routes


def item(key: str, content: str, created: str = "2026-10-27T17:00:00+00:00"):
    return SimpleNamespace(
        key=key,
        value={"content": content, "created_at": created},
        created_at=created,
        updated_at=created,
    )


@pytest.fixture
def listing(monkeypatch):
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "")

    async def run(items: list):
        store = SimpleNamespace(asearch=AsyncMock(return_value=items))
        with (
            patch.object(workspace_routes, "_get_store", AsyncMock(return_value=store)),
            patch.object(
                workspace_routes,
                "_namespaces",
                AsyncMock(return_value=[("default", "u")]),
            ),
        ):
            found = await workspace_routes.list_workspace_files(
                SimpleNamespace(headers={})
            )
        return {f["path"]: f for f in found["files"]}

    return run


@pytest.mark.asyncio
async def test_lists_a_file_the_agent_wrote(listing):
    files = await listing([item("/notes.md", "Hello.")])
    assert "/notes.md" in files


@pytest.mark.asyncio
async def test_reports_how_big_it_is(listing):
    files = await listing([item("/notes.md", "Hello.")])
    assert files["/notes.md"]["bytes"] == 6


@pytest.mark.asyncio
async def test_leaves_the_memory_file_to_the_memories_page(listing):
    """It is already shown there, as facts rather than as a file."""
    files = await listing(
        [item("/user_profile.md", "A fact."), item("/notes.md", "Hi")]
    )
    assert list(files) == ["/notes.md"]


@pytest.mark.asyncio
async def test_says_when_it_was_written(listing):
    files = await listing([item("/notes.md", "Hello.")])
    assert files["/notes.md"]["modified"] == "2026-10-27T17:00:00+00:00"


@pytest.mark.asyncio
async def test_an_entry_with_no_content_is_still_listed(listing):
    store = [
        SimpleNamespace(key="/empty.md", value={}, created_at=None, updated_at=None)
    ]
    files = await listing(store)
    assert files["/empty.md"]["bytes"] == 0


@pytest.mark.asyncio
async def test_a_workspace_with_nothing_in_it(listing):
    assert await listing([]) == {}


@pytest.fixture
def reader(monkeypatch):
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "")

    async def run(items: list, path: str):
        store = SimpleNamespace(asearch=AsyncMock(return_value=items))
        with (
            patch.object(workspace_routes, "_get_store", AsyncMock(return_value=store)),
            patch.object(
                workspace_routes,
                "_namespaces",
                AsyncMock(return_value=[("default", "u")]),
            ),
        ):
            return await workspace_routes.read_workspace_file(
                path, SimpleNamespace(headers={})
            )

    return run


@pytest.mark.asyncio
async def test_hands_back_what_the_agent_wrote(reader):
    found = await reader([item("/notes.md", "Hello.")], "notes.md")
    assert found["content"] == "Hello."


@pytest.mark.asyncio
async def test_a_leading_slash_names_the_same_file(reader):
    found = await reader([item("/notes.md", "Hello.")], "/notes.md")
    assert found["content"] == "Hello."


@pytest.mark.asyncio
async def test_says_which_file_it_is(reader):
    found = await reader([item("/notes.md", "Hello.")], "notes.md")
    assert found["path"] == "/notes.md"


@pytest.mark.asyncio
async def test_a_file_that_is_not_there_is_not_found(reader):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await reader([item("/notes.md", "Hello.")], "missing.md")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_the_memory_file_is_not_served_as_a_workspace_file(reader):
    """It belongs to the memories page, which can delete single facts."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await reader([item("/user_profile.md", "A fact.")], "user_profile.md")
    assert exc.value.status_code == 404


@pytest.fixture
def remover(monkeypatch):
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "")

    async def run(items: list, path: str):
        store = SimpleNamespace(
            asearch=AsyncMock(return_value=items), adelete=AsyncMock()
        )
        with (
            patch.object(workspace_routes, "_get_store", AsyncMock(return_value=store)),
            patch.object(
                workspace_routes,
                "_namespaces",
                AsyncMock(return_value=[("default", "u")]),
            ),
        ):
            await workspace_routes.delete_workspace_file(
                path, SimpleNamespace(headers={})
            )
        return store

    return run


@pytest.mark.asyncio
async def test_deletes_the_file_that_was_named(remover):
    store = await remover([item("/notes.md", "Hello.")], "notes.md")
    assert store.adelete.await_args.args[1] == "/notes.md"


@pytest.mark.asyncio
async def test_leaves_the_other_files_alone(remover):
    store = await remover(
        [item("/notes.md", "Hi"), item("/report.md", "Bye")], "notes.md"
    )
    assert store.adelete.await_count == 1


@pytest.mark.asyncio
async def test_deleting_a_file_that_is_not_there_is_not_found(remover):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await remover([item("/notes.md", "Hello.")], "missing.md")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_the_memory_file_cannot_be_deleted_this_way(remover):
    """Memories are deleted a fact at a time, on their own page."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await remover([item("/user_profile.md", "A fact.")], "user_profile.md")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_a_file_is_named_the_way_the_agent_names_it(listing, monkeypatch):
    """The store drops the route prefix, and a key is not a path."""
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "/reports/")
    files = await listing([item("/notes.md", "Hello.")])
    assert list(files) == ["/reports/notes.md"]


@pytest.mark.asyncio
async def test_a_key_that_already_carries_the_route_is_not_doubled(
    listing, monkeypatch
):
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "/reports/")
    files = await listing([item("/reports/notes.md", "Hello.")])
    assert list(files) == ["/reports/notes.md"]


@pytest.mark.asyncio
async def test_without_a_route_the_key_stands_on_its_own(listing, monkeypatch):
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "")
    files = await listing([item("/notes.md", "Hello.")])
    assert list(files) == ["/notes.md"]


@pytest.mark.asyncio
async def test_the_name_shown_is_a_name_that_can_be_opened(reader, monkeypatch):
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "/reports/")
    found = await reader([item("/notes.md", "Hello.")], "reports/notes.md")
    assert found["content"] == "Hello."


@pytest.mark.asyncio
async def test_the_bare_key_still_opens_it(reader, monkeypatch):
    """What was stored is still what was stored."""
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "/reports/")
    found = await reader([item("/notes.md", "Hello.")], "notes.md")
    assert found["content"] == "Hello."


@pytest.mark.asyncio
async def test_the_name_shown_is_a_name_that_can_be_deleted(remover, monkeypatch):
    monkeypatch.setattr(workspace_routes, "_store_route", lambda: "/reports/")
    store = await remover([item("/notes.md", "Hi")], "reports/notes.md")
    assert store.adelete.await_args.args[1] == "/notes.md"


def test_the_route_is_the_one_configured_to_reach_the_store(monkeypatch):
    monkeypatch.setattr(
        workspace_routes,
        "_filesystem_routes",
        lambda: {"/memories/": "store", "/reports/": "store", "/": "state"},
    )
    assert workspace_routes._store_route() == "/reports/"


def test_a_deployment_that_stores_nothing_has_no_route(monkeypatch):
    monkeypatch.setattr(workspace_routes, "_filesystem_routes", lambda: {"/": "state"})
    assert workspace_routes._store_route() == ""
