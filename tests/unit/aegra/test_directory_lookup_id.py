"""The directory is asked about a username, never a subject."""

from __future__ import annotations

import inspect

import pytest


class TestWhatTheDirectoryMatches:
    def test_it_looks_people_up_by_uid(self):
        from agent.src.ldap import service

        assert "uid=" in inspect.getsource(service)


class TestTheDocumentPage:
    def test_it_asks_with_the_username(self):
        from agent.aegra import knowledge_routes

        assert "memory_user_id" in inspect.getsource(knowledge_routes._teams_of)

    def test_it_does_not_ask_with_the_subject(self):
        from agent.aegra import knowledge_routes

        assert "authenticated_user_id" not in inspect.getsource(
            knowledge_routes._teams_of
        )


class TestTheInboundDoor:
    def test_it_asks_with_the_username(self):
        from agent.aegra import inbound_limit_middleware

        assert "memory_user_id" in inspect.getsource(
            inbound_limit_middleware.teams_with_a_budget
        )

    def test_it_does_not_ask_with_the_subject(self):
        from agent.aegra import inbound_limit_middleware

        assert "authenticated_user_id" not in inspect.getsource(
            inbound_limit_middleware.teams_with_a_budget
        )


class TestTheRunSideWasAlreadyRight:
    def test_it_asks_with_what_the_run_resolved(self):
        from agent.src.infrastructure import middleware

        assert "resolve_user_groups(caller" in inspect.getsource(
            middleware._teams_with_a_budget
        )


class TestTheyAgree:
    @pytest.mark.asyncio
    async def test_a_page_and_a_run_ask_about_the_same_person(self):
        from unittest.mock import patch

        from agent.aegra import knowledge_routes

        class _Request:
            headers = {"x-user-id": "johnwick"}

        asked: list[str] = []

        async def _groups(who, candidates):
            asked.append(who)
            return ()

        with (
            patch("agent.aegra.auth.ENABLE_AUTH", False),
            patch("agent.src.ldap.resolve_user_groups", side_effect=_groups),
            patch("agent.src.knowledge.store.session_store", return_value=_AStore()),
        ):
            await knowledge_routes._teams_of(_Request())

        assert asked == ["johnwick"]


class _AStore:
    @staticmethod
    def documents_in(**_kwargs):
        class _Document:
            team = "platform"

        return [_Document()]


class TestItCannotComeBackQuietly:
    """Every caller of the directory, checked, not just the two."""

    @staticmethod
    def _callers():
        """Every function that asks the directory, by name."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[3] / "services" / "agent"
        found = []
        for path in root.rglob("*.py"):
            if path.name == "service.py":
                continue
            try:
                source = path.read_text()
            except OSError:
                continue
            found.extend(
                (f"{path.name}:{name}", body)
                for name, body in _asking_functions(source)
            )
        return found

    def test_there_are_callers_to_check(self):
        assert len(self._callers()) >= 3

    def test_no_caller_asks_the_directory_about_a_subject(self):
        offenders = [
            where for where, body in self._callers() if "authenticated_user_id" in body
        ]
        assert offenders == [], (
            f"{offenders} ask the directory about a token subject. It matches "
            "uid=<username>, so a subject finds nobody — which reads as "
            "'in no teams' and silently removes every team's access."
        )


def _asking_functions(source: str) -> list[tuple[str, str]]:
    """Functions in this source that ask the directory."""
    import ast

    if "resolve_user_groups(" not in source:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = ast.get_source_segment(source, node) or ""
        if "resolve_user_groups(" in body:
            found.append((node.name, body))
    return found


class TestTheSweepCanActuallyFail:
    """Planted sources, because a green sweep proves nothing."""

    WRONG = (
        "async def teams_of(request):\n"
        "    who = await authenticated_user_id(request)\n"
        "    return await resolve_user_groups(who, names)\n"
    )
    RIGHT = (
        "async def teams_of(request):\n"
        "    who = await memory_user_id(request)\n"
        "    return await resolve_user_groups(who, names)\n"
    )

    def test_a_subject_lookup_is_found(self):
        found = _asking_functions(self.WRONG)
        assert [name for name, body in found if "authenticated_user_id" in body] == [
            "teams_of"
        ]

    def test_a_username_lookup_is_not(self):
        found = _asking_functions(self.RIGHT)
        assert [name for name, body in found if "authenticated_user_id" in body] == []

    def test_a_module_that_uses_the_subject_elsewhere_is_left_alone(self):
        both = (
            "async def who_is_calling(request):\n"
            "    return await authenticated_user_id(request)\n"
            "\n"
            "async def teams_of(request):\n"
            "    who = await memory_user_id(request)\n"
            "    return await resolve_user_groups(who, names)\n"
        )
        found = _asking_functions(both)
        assert [name for name, body in found if "authenticated_user_id" in body] == []

    def test_a_module_that_never_asks_contributes_nothing(self):
        assert _asking_functions("def f():\n    return 1\n") == []

    def test_a_file_that_will_not_parse_is_not_a_crash(self):
        assert _asking_functions("resolve_user_groups( def (((") == []
